from __future__ import annotations

import hashlib
import itertools
import json
from datetime import datetime, timezone

from app.models import (
    AutomatedPanelResearchRequest,
    AutomatedPanelResearchResponse,
    AutomatedSelectedConfiguration,
    BacktestRunRequest,
    MarketType,
    QuantDatasetManifest,
    QuantValidationRequest,
    StrategyPanelValidationRequest,
    StrategyReturnSeries,
)
from app.services.backtest_service import BacktestService
from app.services.database_service import DatabaseManager
from app.services.deflated_performance_service import DeflatedPerformanceService
from app.services.historical_data_service import HistoricalDataError, HistoricalDatasetStore
from app.services.quant_validation_service import QuantValidationService
from app.services.strategy_panel_service import StrategyPanelValidationService


class AutomatedPanelError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ResearchExperimentStore:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def acquire(
        self,
        user_id: int,
        request: AutomatedPanelResearchRequest,
        dataset_sha: str,
        request_sha: str,
        development_end: int,
        holdout_start: int,
        holdout_end: int,
    ) -> AutomatedPanelResearchResponse | None:
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM research_experiments WHERE user_id = ? AND experiment_id = ? AND version = ?",
                (user_id, request.experiment_id, request.experiment_version),
            ).fetchone()
            if row is not None:
                if row["request_sha256"] != request_sha or row["dataset_sha256"] != dataset_sha:
                    raise AutomatedPanelError("immutable_experiment_version_conflict")
                if row["result_json"]:
                    response = AutomatedPanelResearchResponse.model_validate_json(row["result_json"])
                    return response.model_copy(update={"experiment_reused": True})
                conn.execute(
                    "UPDATE research_experiments SET status = ?, updated_at = ? WHERE id = ?",
                    ("running", now, row["id"]),
                )
                conn.commit()
                return None
            conn.execute(
                """
                INSERT INTO research_experiments (
                    user_id, experiment_id, version, dataset_id, dataset_version,
                    dataset_sha256, request_sha256, development_end_index,
                    holdout_start_index, holdout_end_index, status, result_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    request.experiment_id,
                    request.experiment_version,
                    request.dataset_id,
                    request.dataset_version,
                    dataset_sha,
                    request_sha,
                    development_end,
                    holdout_start,
                    holdout_end,
                    "running",
                    None,
                    now,
                    now,
                ),
            )
            conn.commit()
        return None

    def complete(
        self,
        user_id: int,
        request: AutomatedPanelResearchRequest,
        response: AutomatedPanelResearchResponse,
    ) -> None:
        with self.database.connection() as conn:
            conn.execute(
                """
                UPDATE research_experiments
                SET status = ?, result_json = ?, updated_at = ?
                WHERE user_id = ? AND experiment_id = ? AND version = ?
                """,
                (
                    "complete",
                    response.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                    user_id,
                    request.experiment_id,
                    request.experiment_version,
                ),
            )
            conn.commit()

    def fail(self, user_id: int, request: AutomatedPanelResearchRequest) -> None:
        with self.database.connection() as conn:
            conn.execute(
                """
                UPDATE research_experiments SET status = ?, updated_at = ?
                WHERE user_id = ? AND experiment_id = ? AND version = ?
                """,
                (
                    "failed",
                    datetime.now(timezone.utc).isoformat(),
                    user_id,
                    request.experiment_id,
                    request.experiment_version,
                ),
            )
            conn.commit()


class AutomatedPanelResearchService:
    def __init__(
        self,
        database: DatabaseManager,
        dataset_store: HistoricalDatasetStore,
        backtest_service: BacktestService,
        panel_service: StrategyPanelValidationService,
        quant_service: QuantValidationService,
        deflated_service: DeflatedPerformanceService,
    ) -> None:
        self.database = database
        self.dataset_store = dataset_store
        self.backtest_service = backtest_service
        self.panel_service = panel_service
        self.quant_service = quant_service
        self.deflated_service = deflated_service
        self.experiments = ResearchExperimentStore(database)

    def _fingerprint(self, payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _stored_dataset(self, user_id: int, dataset_id: str, version: str):
        try:
            manifest = self.dataset_store.get_manifest(user_id, dataset_id, version)
            candles = self.dataset_store.load_candles(user_id, dataset_id, version)
        except HistoricalDataError as exc:
            raise AutomatedPanelError(exc.code) from exc
        return manifest, candles

    def _run_config(self, manifest, candles, config, request):
        run_request = BacktestRunRequest(
            symbol=manifest.symbol,
            market=manifest.market,
            timeframe=manifest.timeframe,
            window_size=config[0],
            lookahead_candles=config[1],
            score_threshold=config[2],
            max_signals=request.max_signals_per_strategy,
            take_profit_index=config[3],
            risk_settings=request.risk_settings,
            trade_stats=request.trade_stats,
            execution=request.execution,
        )
        summary = self.backtest_service.run(run_request, candles)
        timestamp_index = {item.timestamp.isoformat(): index for index, item in enumerate(candles)}
        dense = [0.0] * len(candles)
        for item in summary.items:
            if not item.activated:
                continue
            decision_index = timestamp_index.get(item.signal_time)
            if decision_index is None or decision_index + 1 >= len(dense):
                raise AutomatedPanelError("panel_trade_timestamp_not_found")
            dense[decision_index + 1] += item.rr_realized
        return run_request, summary, dense

    def run(
        self,
        user_id: int,
        request: AutomatedPanelResearchRequest,
    ) -> AutomatedPanelResearchResponse:
        dataset, candles = self._stored_dataset(
            user_id, request.dataset_id, request.dataset_version
        )
        manifest = dataset.manifest
        holdout_size = max(100, int(len(candles) * request.holdout_fraction))
        holdout_start = len(candles) - holdout_size
        development_end = holdout_start - request.holdout_embargo_bars - 1
        holdout_end = len(candles) - 1
        if development_end < max(request.window_sizes) + max(request.lookahead_options) + 20:
            raise AutomatedPanelError("dataset_too_small_for_locked_development_holdout_split")
        request_sha = self._fingerprint(
            {
                "method": "automated_panel_final_holdout_v1",
                "dataset_sha": dataset.canonical_sha256,
                "request": request.model_dump(mode="json"),
                "partition": [development_end, holdout_start, holdout_end],
            }
        )
        reused = self.experiments.acquire(
            user_id,
            request,
            dataset.canonical_sha256,
            request_sha,
            development_end,
            holdout_start,
            holdout_end,
        )
        if reused is not None:
            return reused
        try:
            response = self._execute(
                user_id,
                request,
                dataset,
                candles,
                request_sha,
                development_end,
                holdout_start,
                holdout_end,
            )
            self.experiments.complete(user_id, request, response)
            return response
        except Exception:
            self.experiments.fail(user_id, request)
            raise

    def _execute(
        self,
        user_id: int,
        request: AutomatedPanelResearchRequest,
        dataset,
        candles,
        request_sha: str,
        development_end: int,
        holdout_start: int,
        holdout_end: int,
    ) -> AutomatedPanelResearchResponse:
        manifest = dataset.manifest
        development = candles[: development_end + 1]
        configs = list(
            itertools.product(
                sorted(set(request.window_sizes)),
                sorted(set(request.lookahead_options)),
                sorted(set(request.score_thresholds)),
                sorted(set(request.take_profit_indices)),
            )
        )
        strategies = []
        config_map = {}
        summary_map = {}
        panel_dense_returns: list[list[float]] = []
        for window, lookahead, threshold, tp_index in configs:
            config = (window, lookahead, float(threshold), tp_index)
            run_request, summary, dense = self._run_config(
                manifest, development, config, request
            )
            if summary.activated_signals < request.minimum_development_trades:
                continue
            strategy_id = f"w{window}-l{lookahead}-t{float(threshold):g}-tp{tp_index}"
            strategies.append(
                StrategyReturnSeries(
                    strategy_id=strategy_id,
                    strategy_version=request.experiment_version,
                    returns_rr=dense,
                )
            )
            panel_dense_returns.append(dense)
            config_map[strategy_id] = config
            summary_map[strategy_id] = summary

        base_payload = {
            "experiment_ref": f"{request.experiment_id}:{request.experiment_version}",
            "experiment_fingerprint": request_sha,
            "dataset_ref": dataset.dataset_ref,
            "canonical_sha256": dataset.canonical_sha256,
            "development_start_index": 0,
            "development_end_index": development_end,
            "holdout_start_index": holdout_start,
            "holdout_end_index": holdout_end,
            "holdout_embargo_bars": request.holdout_embargo_bars,
            "parameter_combinations": len(configs),
            "eligible_panel_strategies": len(strategies),
            "limitations": [
                "The final holdout is locked by immutable experiment ID/version before panel generation.",
                "Repeated experiments with new IDs can still consume holdout evidence and must be counted in governance.",
                "PBO/PSR/DSR diagnostics do not prove future profitability or authorize live execution.",
            ],
            "actionable_for_live": False,
        }
        if len(strategies) < 3:
            return AutomatedPanelResearchResponse(
                **base_payload,
                status="INCONCLUSIVE",
                hard_gates={"minimum_three_eligible_strategies": False},
                failed_gates=["minimum_three_eligible_strategies"],
            )

        panel_manifest = QuantDatasetManifest(
            dataset_id=f"{manifest.dataset_id}-development-panel",
            version=f"{manifest.version}-{request_sha[:12]}",
            source="automated_parameter_panel_development",
            symbol=manifest.symbol,
            market=manifest.market,
            timeframe=manifest.timeframe,
            start_time=development[0].timestamp,
            end_time=development[-1].timestamp,
            sample_count=len(development),
            source_sha256=request_sha,
            is_point_in_time=manifest.is_point_in_time,
            is_survivorship_bias_controlled=manifest.is_survivorship_bias_controlled,
            is_independent_holdout=False,
            data_quality_score=manifest.data_quality_score,
        )
        panel = self.panel_service.validate(
            StrategyPanelValidationRequest(
                panel_id=request.experiment_id,
                panel_version=request.experiment_version,
                dataset=panel_manifest,
                strategies=strategies,
                timestamps=[item.timestamp for item in development],
                block_count=request.pbo_block_count,
                selection_metric=request.selection_metric,
            )
        )
        selected_id = panel.most_selected_strategy_id
        if panel.status != "ROBUSTNESS_CANDIDATE" or not selected_id:
            status = "HIGH_OVERFIT_RISK" if panel.status == "HIGH_OVERFIT_RISK" else "INCONCLUSIVE"
            return AutomatedPanelResearchResponse(
                **base_payload,
                status=status,
                panel_validation=panel,
                hard_gates={"panel_robustness": False},
                failed_gates=["panel_robustness"],
            )

        selected_config = config_map[selected_id]
        selected_development = summary_map[selected_id]
        window, lookahead, threshold, tp_index = selected_config
        context_start = max(0, holdout_start - window)
        holdout_context = candles[context_start : holdout_end + 1]
        holdout_request = BacktestRunRequest(
            symbol=manifest.symbol,
            market=manifest.market,
            timeframe=manifest.timeframe,
            window_size=window,
            lookahead_candles=lookahead,
            score_threshold=threshold,
            max_signals=request.max_signals_per_strategy,
            take_profit_index=tp_index,
            risk_settings=request.risk_settings,
            trade_stats=request.trade_stats,
            execution=request.execution,
        )
        results = self.backtest_service._generate_results(
            holdout_request,
            holdout_context,
            start_index=holdout_start - context_start,
            end_index=len(holdout_context) - lookahead + 1,
        )
        holdout_summary = self.backtest_service._summarize_results(
            holdout_request, len(holdout_context), results
        )
        activated = [item for item in results if item.activated]
        global_index = {item.timestamp.isoformat(): index for index, item in enumerate(candles)}
        holdout_sparse_returns = []
        holdout_sparse_times = []
        holdout_source_indices = []
        holdout_benchmark = []
        holdout_dense = [0.0] * (holdout_end - holdout_start + 1)
        for item in activated:
            decision_index = global_index.get(item.signal_time)
            if decision_index is None:
                raise AutomatedPanelError("holdout_trade_timestamp_not_found")
            source_index = decision_index + 1
            if source_index < holdout_start or source_index > holdout_end:
                raise AutomatedPanelError("holdout_trade_outside_locked_boundary")
            local_index = source_index - holdout_start
            holdout_dense[local_index] += item.rr_realized
            risk_distance = abs(item.entry_price - item.stop_loss)
            entry_index = min(holdout_end, source_index + max(0, item.bars_to_entry - 1))
            exit_index = min(holdout_end, entry_index + max(0, item.bars_held - 1))
            benchmark_rr = (
                (candles[exit_index].close - item.entry_price) / risk_distance
                if risk_distance > 0
                else 0.0
            )
            holdout_sparse_returns.append(item.rr_realized)
            holdout_sparse_times.append(candles[source_index].timestamp)
            holdout_source_indices.append(source_index)
            holdout_benchmark.append(round(benchmark_rr, 6))

        deflated = self.deflated_service.evaluate(
            holdout_dense,
            panel_dense_returns,
            active_return_count=len(holdout_sparse_returns),
        )
        quant = None
        if len(holdout_sparse_returns) >= 30:
            holdout_sha = self._fingerprint(
                {
                    "experiment": request_sha,
                    "selected": selected_id,
                    "returns": holdout_sparse_returns,
                    "indices": holdout_source_indices,
                }
            )
            holdout_manifest = QuantDatasetManifest(
                dataset_id=f"{manifest.dataset_id}-final-holdout",
                version=f"{manifest.version}-{holdout_sha[:12]}",
                source="immutable_automated_final_holdout",
                symbol=manifest.symbol,
                market=manifest.market,
                timeframe=manifest.timeframe,
                start_time=holdout_sparse_times[0],
                end_time=holdout_sparse_times[-1],
                sample_count=len(holdout_sparse_returns),
                source_sha256=holdout_sha,
                is_point_in_time=manifest.is_point_in_time,
                is_survivorship_bias_controlled=manifest.is_survivorship_bias_controlled,
                is_independent_holdout=True,
                data_quality_score=manifest.data_quality_score,
            )
            quant = self.quant_service.validate(
                QuantValidationRequest(
                    strategy_id=selected_id,
                    strategy_version=request.experiment_version,
                    dataset=holdout_manifest,
                    returns_rr=holdout_sparse_returns,
                    timestamps=holdout_sparse_times,
                    return_source_indices=holdout_source_indices,
                    benchmark_returns_rr=holdout_benchmark,
                    strategies_tried=len(configs),
                    bootstrap_samples=request.bootstrap_samples,
                    monte_carlo_paths=request.monte_carlo_paths,
                    random_seed=request.random_seed,
                )
            )

        gates = {
            "panel_robustness": panel.status == "ROBUSTNESS_CANDIDATE",
            "minimum_holdout_trades": len(holdout_sparse_returns) >= request.minimum_holdout_trades,
            "positive_holdout_net_rr": holdout_summary.net_rr > 0.0,
            "positive_holdout_expectancy_interval": bool(
                quant and quant.expectancy_interval.lower > 0.0
            ),
            "holdout_market_baseline_outperformance": bool(
                quant
                and quant.benchmark_difference_interval
                and quant.benchmark_difference_interval.lower > 0.0
            ),
            "multiple_testing_adjusted_significance": bool(
                quant and quant.multiple_testing_adjusted_significant
            ),
            "deflated_performance": deflated.eligible,
            "dataset_point_in_time": manifest.is_point_in_time,
            "survivorship_bias_controlled": manifest.is_survivorship_bias_controlled,
            "data_quality": manifest.data_quality_score >= 90.0,
            "live_execution_disabled": True,
        }
        failed = [name for name, passed in gates.items() if not passed]
        status = "FINAL_HOLDOUT_CANDIDATE" if not failed else "HOLDOUT_FAILED"
        return AutomatedPanelResearchResponse(
            **base_payload,
            status=status,
            panel_validation=panel,
            selected_configuration=AutomatedSelectedConfiguration(
                strategy_id=selected_id,
                window_size=window,
                lookahead_candles=lookahead,
                score_threshold=threshold,
                take_profit_index=tp_index,
                development_activated_trades=selected_development.activated_signals,
                development_net_rr=selected_development.net_rr,
                development_expectancy_rr=selected_development.expectancy_rr,
            ),
            holdout_backtest=holdout_summary,
            holdout_quant_validation=quant,
            deflated_performance=deflated,
            hard_gates=gates,
            failed_gates=failed,
        )
