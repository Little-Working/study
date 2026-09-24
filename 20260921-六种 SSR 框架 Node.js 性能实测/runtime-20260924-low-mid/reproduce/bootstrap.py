from common import *
for name in ['gc-stats','metrics']:
 (OUT/(name+'-selftest.log')).write_text(docker('exec','ssrbench3-builder','node',f'/bench/__tests__/{name}.test.cjs'))
# Check actual image/API and helper service before beginning formal measurement.
(OUT/'node-perf-api.json').write_text(docker('exec','ssrbench3-builder','node','-e',"const p=require('node:perf_hooks');const h=p.monitorEventLoopDelay({resolution:10});console.log(JSON.stringify({node:process.version,resolutionMs:10,count:typeof h.count,takeRecords:typeof p.PerformanceObserver.prototype.takeRecords,constants:p.constants}))"))
assert docker('inspect','-f','{{.State.Running}}','ssrbench3-backend')=='true'
docker('stop','ssrbench3-builder')
print('Runtime monitor selftests passed, build container stopped.',flush=True)
