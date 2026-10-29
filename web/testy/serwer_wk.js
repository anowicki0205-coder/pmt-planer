// Serwer plików dla testów w prawdziwym WebKit (Safari): wstrzykuje do index.html zbieranie błędów (window.__bledy). Port wypisuje na stdout.
const { serwer } = require('./wspolne');
const WSTRZYKNIECIE = `window.__bledy=[];addEventListener('error',e=>window.__bledy.push('ERR '+e.message+' @'+(e.filename||'').split('/').pop()+':'+e.lineno));addEventListener('unhandledrejection',e=>window.__bledy.push('REJ '+(e.reason&&e.reason.message||e.reason)));const ce=console.error;console.error=function(){window.__bledy.push('CONSOLE '+[].slice.call(arguments).join(' ').slice(0,200));ce.apply(console,arguments)};`;
serwer({ sekret: 'SEKRET-TESTOWY', wstrzyknij: WSTRZYKNIECIE }).then(s => { console.log('PORT=' + s.port); });
