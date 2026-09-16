"""Untrusted execution harness. Its result is compared by the external grader."""
import json
import traceback
from pathlib import Path
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType

payload=json.loads(Path('/input.json').read_text())
try:
    spark=(SparkSession.builder.master('local[2]').appName('Graphlab exercise')
        .config('spark.ui.enabled','false').config('spark.sql.session.timeZone','UTC')
        .config('spark.driver.bindAddress','127.0.0.1').config('spark.driver.host','127.0.0.1')
        .config('spark.sql.shuffle.partitions','2').config('spark.driver.memory','1g')
        .config('spark.sql.warehouse.dir','/tmp/warehouse').getOrCreate())
    spark.sparkContext.setLogLevel('ERROR')
    fixture=payload['fixture']
    namespace={'spark':spark,'__name__':'__exercise__'}
    for name,table in fixture['tables'].items():
        df=spark.createDataFrame(table['rows'],StructType.fromJson(table['schema']))
        df.createOrReplaceTempView(name)
        namespace[name]=df
    # This exec is deliberately inside a disposable, network-denied sandbox.
    exec(compile(payload['files']['main.py'],'main.py','exec'),namespace)
    output=namespace.get('result')
    if not isinstance(output,DataFrame):
        raise ValueError('Assign your output DataFrame to result')
    rows=output.limit(2001).collect()
    if len(rows)>2000:
        raise ValueError('Output exceeds 2,000 rows; reduce the result to the requested fields and records')
    result={'schema':output.schema.jsonValue(),'rows':[r.asDict(recursive=True) for r in rows], 'plan':output._jdf.queryExecution().toString()[:12000]}
    spark.stop()
except Exception as exc:
    result={'error':traceback.format_exc()[:2500]}
Path('/output/result.json').write_text(json.dumps(result,default=str))
