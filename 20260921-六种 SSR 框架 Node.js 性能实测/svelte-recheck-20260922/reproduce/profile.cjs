const inspector = require('node:inspector');
const fs = require('node:fs');
const session = new inspector.Session();
session.connect();
let running = false;
process.on('SIGUSR2', () => {
  if (!running) {
    session.post('Profiler.enable', () => session.post('Profiler.start', () => {
      running = true;
      fs.writeFileSync('/bench/profile-started', 'yes');
    }));
  } else {
    session.post('Profiler.stop', (err, result) => {
      if (err) throw err;
      fs.writeFileSync('/bench/profile.cpuprofile', JSON.stringify(result.profile));
      running = false;
      session.disconnect();
    });
  }
});
