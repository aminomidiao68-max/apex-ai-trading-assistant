from __future__ import annotations
import math
from datetime import datetime,timedelta,timezone
import pytest
from app.models import Candle,MarketType,OperationalDriftRequest,OperationalSloRequest,PaperCorrelationDatasetRef,QuantDatasetManifest
from app.services.database_service import DatabaseManager,LATEST_SCHEMA_VERSION
from app.services.historical_data_service import HistoricalDatasetStore
from app.services.operational_validation_service import OperationalValidationService,OperationalValidationError

def save(store,did,returns):
 start=datetime(2025,1,1,tzinfo=timezone.utc);close=100.;candles=[Candle(timestamp=start,open=100,high=101,low=99,close=100,volume=1)]
 for i,r in enumerate(returns,1):
  old=close;close*=math.exp(r);candles.append(Candle(timestamp=start+timedelta(hours=i),open=old,high=max(old,close),low=min(old,close),close=close,volume=1))
 m=QuantDatasetManifest(dataset_id=did,version='v1',source='drift_fixture',symbol='BTCUSDT',market=MarketType.crypto,timeframe='1h',start_time=candles[0].timestamp,end_time=candles[-1].timestamp,sample_count=len(candles),source_sha256='a'*64,is_point_in_time=True,data_quality_score=100)
 store.save(1,m,('b' if did=='base' else 'c')*64,candles)

def test_drift_stable_blocked_idempotent_and_non_actionable(tmp_path):
 db=DatabaseManager(db_path=str(tmp_path/'d.db'));store=HistoricalDatasetStore(db);svc=OperationalValidationService(db,store)
 base=[.001*math.sin(i/5) for i in range(120)];save(store,'base',base);save(store,'candidate',[x*1.02 for x in base])
 req=OperationalDriftRequest(run_id='operational-drift-0001',baseline=PaperCorrelationDatasetRef(dataset_id='base',version='v1'),candidate=PaperCorrelationDatasetRef(dataset_id='candidate',version='v1'),minimum_observations=60)
 first=svc.run_drift(1,req);second=svc.run_drift(1,req)
 assert first.status=='STABLE';assert first.probability_claimed is False;assert first.actionable_for_live is False;assert second.duplicate is True
 assert db.schema_version()==LATEST_SCHEMA_VERSION==14

def test_slo_insufficient_within_and_breach():
 insufficient=OperationalValidationService.evaluate_slo({'requests_total':5,'sample_window':5,'server_errors_total':0,'latency_p95_ms':100},OperationalSloRequest(minimum_samples=20))
 assert insufficient.status=='INSUFFICIENT_EVIDENCE'
 good=OperationalValidationService.evaluate_slo({'requests_total':100,'sample_window':100,'server_errors_total':0,'latency_p95_ms':200},OperationalSloRequest())
 assert good.status=='WITHIN_SLO'
 bad=OperationalValidationService.evaluate_slo({'requests_total':100,'sample_window':100,'server_errors_total':5,'latency_p95_ms':3000},OperationalSloRequest())
 assert bad.status=='SLO_BREACH';assert set(bad.failed_gates)=={'p95_latency_slo','server_error_rate_slo'}
