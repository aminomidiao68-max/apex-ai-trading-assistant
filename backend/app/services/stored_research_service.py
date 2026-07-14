from __future__ import annotations

import hashlib
import json
from datetime import datetime

from app.models import (
    BacktestRunRequest,
    BacktestSweepRequest,
    MarketType,
    QuantDatasetManifest,
    QuantValidationRequest,
    QuantWalkForwardFold,
    StoredBacktestResearchRequest,
    StoredBacktestResearchResponse,
    StoredWalkForwardFoldResult,
    StoredWalkForwardResearchRequest,
    StoredWalkForwardResearchResponse,
)
from app.services.backtest_service import BacktestService
from app.services.historical_data_service import HistoricalDatasetStore, HistoricalDataError
from app.services.quant_validation_service import QuantValidationService


class StoredResearchError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class StoredResearchService:
    def __init__(
        self,
        dataset_store: HistoricalDatasetStore,
        backtest_service: BacktestService,
        quant_service: QuantValidationService,
    ) -> None:
        self.dataset_store = dataset_store
        self.backtest_service = backtest_service
        self.quant_service = quant_service

    def _dataset(self, user_id: int, dataset_id: str, version: str):
        try:
            manifest_response = self.dataset_store.get_manifest(user_id, dataset_id, version)
            candles = self.dataset_store.load_candles(user_id, dataset_id, version)
        except HistoricalDataError as exc:
            raise StoredResearchError(exc.code) from exc
        if len(candles) != manifest_response.stored_candle_count:
            raise StoredResearchError("stored_dataset_count_mismatch")
        return manifest_response, candles

    def _configuration_fingerprint(self, payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def run_fixed_backtest(
        self,
        user_id: int,
        request: StoredBacktestResearchRequest,
    ) -> StoredBacktestResearchResponse:
        dataset, candles = self._dataset(user_id, request.dataset_id, request.dataset_version)
        manifest = dataset.manifest
        config_payload = request.model_dump(mode="json", exclude={"dataset_id", "dataset_version"})
        fingerprint = self._configuration_fingerprint(config_payload)
        run_request = BacktestRunRequest(
            symbol=manifest.symbol,
            market=manifest.market,
            timeframe=manifest.timeframe,
            window_size=request.window_size,
            lookahead_candles=request.lookahead_candles,
            score_threshold=request.score_threshold,
            max_signals=request.max_signals,
            take_profit_index=request.take_profit_index,
            risk_settings=request.risk_settings,
            trade_stats=request.trade_stats,
            execution=request.execution,
        )
        if len(candles) < request.window_size + request.lookahead_candles + 5:
            raise StoredResearchError("stored_dataset_too_small_for_backtest")
        summary = self.backtest_service.run(run_request, candles)
        frozen_before = bool(
            request.configuration_frozen_at
            and request.configuration_frozen_at.tzinfo is not None
            and request.configuration_frozen_at < manifest.start_time
            and manifest.is_independent_holdout
        )
        scope = "fixed_config_holdout" if frozen_before else "retrospective_not_holdout"
        limitations = [
            "A full-dataset backtest does not prove future profitability.",
            "Live execution remains unauthorized.",
        ]
        if not frozen_before:
            limitations.append(
                "Configuration was not proven frozen before an independently held-out dataset; results are retrospective."
            )
        return StoredBacktestResearchResponse(
            dataset_ref=dataset.dataset_ref,
            canonical_sha256=dataset.canonical_sha256,
            configuration_id=request.configuration_id,
            configuration_fingerprint=fingerprint,
            configuration_frozen_before_dataset=frozen_before,
            evaluation_scope=scope,
            backtest=summary,
            limitations=limitations,
            actionable_for_live=False,
        )

    def run_purged_walk_forward(
        self,
        user_id: int,
        request: StoredWalkForwardResearchRequest,
    ) -> StoredWalkForwardResearchResponse:
        dataset, candles = self._dataset(user_id, request.dataset_id, request.dataset_version)
        manifest = dataset.manifest
        combinations = (
            len(set(request.window_sizes))
            * len(set(request.lookahead_options))
            * len(set(request.score_thresholds))
            * len(set(request.take_profit_indices))
        )
        cursor = 0
        fold_results: list[StoredWalkForwardFoldResult] = []
        quant_folds: list[QuantWalkForwardFold] = []
        oos_returns: list[float] = []
        oos_timestamps: list[datetime] = []
        oos_source_indices: list[int] = []
        skipped_folds = 0
        timestamp_index = {candle.timestamp.isoformat(): index for index, candle in enumerate(candles)}

        while len(fold_results) + skipped_folds < request.max_folds:
            train_start = cursor
            train_end = train_start + request.train_size - 1
            test_start = train_end + request.embargo_bars + 1
            test_end = test_start + request.test_size - 1
            if test_end >= len(candles):
                break
            training = candles[train_start : train_end + 1]
            sweep = self.backtest_service.run_sweep(
                BacktestSweepRequest(
                    symbol=manifest.symbol,
                    market=manifest.market,
                    timeframe=manifest.timeframe,
                    window_sizes=request.window_sizes,
                    lookahead_options=request.lookahead_options,
                    score_thresholds=request.score_thresholds,
                    take_profit_indices=request.take_profit_indices,
                    max_signals=request.max_signals_per_fold,
                    max_results=3,
                    minimum_activated_trades=request.minimum_activated_trades,
                    risk_settings=request.risk_settings,
                    trade_stats=request.trade_stats,
                    execution=request.execution,
                ),
                training,
            )
            selected = sweep.best_by_net_rr
            if selected is None:
                skipped_folds += 1
                cursor += request.step_size
                continue

            context_start = max(0, test_start - selected.window_size)
            test_context = candles[context_start : test_end + 1]
            test_request = BacktestRunRequest(
                symbol=manifest.symbol,
                market=manifest.market,
                timeframe=manifest.timeframe,
                window_size=selected.window_size,
                lookahead_candles=selected.lookahead_candles,
                score_threshold=selected.score_threshold,
                max_signals=request.max_signals_per_fold,
                take_profit_index=selected.take_profit_index,
                risk_settings=request.risk_settings,
                trade_stats=request.trade_stats,
                execution=request.execution,
            )
            results = self.backtest_service._generate_results(
                test_request,
                test_context,
                start_index=test_start - context_start,
                end_index=len(test_context) - selected.lookahead_candles + 1,
            )
            summary = self.backtest_service._summarize_results(
                test_request,
                len(test_context),
                results,
            )
            activated = [item for item in results if item.activated]
            fold_returns: list[float] = []
            fold_indices: list[int] = []
            fold_times: list[datetime] = []
            for item in activated:
                decision_index = timestamp_index.get(item.signal_time)
                if decision_index is None:
                    raise StoredResearchError("trade_timestamp_not_found_in_dataset")
                source_index = decision_index + 1
                if source_index < test_start or source_index > test_end:
                    raise StoredResearchError("oos_trade_outside_test_boundary")
                fold_returns.append(item.rr_realized)
                fold_indices.append(source_index)
                fold_times.append(candles[source_index].timestamp)

            selected_id = (
                f"w{selected.window_size}-l{selected.lookahead_candles}-"
                f"t{selected.score_threshold:g}-tp{selected.take_profit_index}"
            )
            fold_payload = {
                "dataset_sha": dataset.canonical_sha256,
                "train": [train_start, train_end],
                "test": [test_start, test_end],
                "embargo": request.embargo_bars,
                "selected": selected_id,
                "returns": fold_returns,
            }
            fold_fingerprint = self._configuration_fingerprint(fold_payload)
            fold_id = f"fold-{len(fold_results) + 1:02d}"
            fold_results.append(
                StoredWalkForwardFoldResult(
                    fold_id=fold_id,
                    train_start_index=train_start,
                    train_end_index=train_end,
                    test_start_index=test_start,
                    test_end_index=test_end,
                    embargo_bars=request.embargo_bars,
                    selected_config_id=selected_id,
                    selected_window_size=selected.window_size,
                    selected_lookahead_candles=selected.lookahead_candles,
                    selected_score_threshold=selected.score_threshold,
                    selected_take_profit_index=selected.take_profit_index,
                    training_net_rr=selected.net_rr,
                    training_win_rate=selected.win_rate,
                    test_summary=summary,
                    oos_return_count=len(fold_returns),
                    fold_fingerprint=fold_fingerprint,
                )
            )
            if fold_returns:
                quant_folds.append(
                    QuantWalkForwardFold(
                        fold_id=fold_id,
                        train_start_index=train_start,
                        train_end_index=train_end,
                        test_start_index=test_start,
                        test_end_index=test_end,
                        embargo_bars=request.embargo_bars,
                        selected_config_id=selected_id,
                        test_returns_rr=fold_returns,
                        test_return_indices=fold_indices,
                    )
                )
                oos_returns.extend(fold_returns)
                oos_timestamps.extend(fold_times)
                oos_source_indices.extend(fold_indices)
            cursor += request.step_size

        quant_validation = None
        limitations = [
            "Each configuration is selected on training data and evaluated only after an embargo.",
            "Zero-edge benchmark is a null baseline, not buy-and-hold or an investable benchmark.",
            "Walk-forward evidence does not prove future profitability or authorize live execution.",
        ]
        if skipped_folds:
            limitations.append(f"Skipped {skipped_folds} folds without a training candidate meeting minimum trade evidence.")

        if len(oos_returns) >= 30 and len(quant_folds) >= 3:
            evidence_payload = {
                "dataset_sha": dataset.canonical_sha256,
                "request": request.model_dump(mode="json"),
                "fold_fingerprints": [item.fold_fingerprint for item in fold_results],
            }
            evidence_sha = self._configuration_fingerprint(evidence_payload)
            derived_manifest = QuantDatasetManifest(
                dataset_id=f"{manifest.dataset_id}-oos-trades",
                version=f"{manifest.version}-{evidence_sha[:12]}",
                source="stored_purged_walk_forward_oos",
                symbol=manifest.symbol,
                market=manifest.market,
                timeframe=manifest.timeframe,
                start_time=oos_timestamps[0],
                end_time=oos_timestamps[-1],
                sample_count=len(oos_returns),
                source_sha256=evidence_sha,
                is_point_in_time=manifest.is_point_in_time,
                is_survivorship_bias_controlled=manifest.is_survivorship_bias_controlled,
                is_independent_holdout=True,
                data_quality_score=manifest.data_quality_score,
                notes=[
                    "Returns are sparse activated trades from non-overlapping OOS test windows.",
                    "Strategy parameters were selected only on each preceding training window.",
                ],
            )
            quant_validation = self.quant_service.validate(
                QuantValidationRequest(
                    strategy_id="apex-stored-walk-forward",
                    strategy_version="stored-research-v1",
                    dataset=derived_manifest,
                    returns_rr=oos_returns,
                    timestamps=oos_timestamps,
                    return_source_indices=oos_source_indices,
                    benchmark_returns_rr=[0.0] * len(oos_returns),
                    walk_forward_folds=quant_folds,
                    strategies_tried=min(100_000, combinations * max(1, len(fold_results))),
                    bootstrap_samples=request.bootstrap_samples,
                    monte_carlo_paths=request.monte_carlo_paths,
                    risk_fraction_per_trade=request.risk_fraction_per_trade,
                    ruin_drawdown_threshold=request.ruin_drawdown_threshold,
                    max_allowed_drawdown_rr=request.max_allowed_drawdown_rr,
                    max_allowed_ruin_probability=request.max_allowed_ruin_probability,
                    random_seed=request.random_seed,
                )
            )
            status = quant_validation.status
        else:
            status = "INSUFFICIENT_EVIDENCE"
            limitations.append("At least 30 activated OOS trades across three non-empty folds are required for Quant Validation.")

        return StoredWalkForwardResearchResponse(
            dataset_ref=dataset.dataset_ref,
            canonical_sha256=dataset.canonical_sha256,
            status=status,
            fold_count=len(fold_results),
            combinations_per_fold=combinations,
            total_oos_activated_trades=len(oos_returns),
            aggregate_oos_net_rr=round(sum(oos_returns), 6),
            folds=fold_results,
            quant_validation=quant_validation,
            limitations=limitations,
            actionable_for_live=False,
        )
