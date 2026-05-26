<?php

/*
 * Plugin API endpoints for fpp-matrixscroller.
 * FPP mounts these under /api/plugin/fpp-matrixscroller/
 * and proxies them to the Python daemon on port 32329.
 *
 * Function name: hyphens removed from plugin name per FPP convention.
 */

function getEndpointsfppmatrixscroller() {
    $result = array();

    $eps = array(
        array('method' => 'GET',  'endpoint' => 'status',  'callback' => 'fppmatrixscrollerStatus'),
        array('method' => 'GET',  'endpoint' => 'config',  'callback' => 'fppmatrixscrollerGetConfig'),
        array('method' => 'GET',  'endpoint' => 'models',  'callback' => 'fppmatrixscrollerModels'),
        array('method' => 'POST', 'endpoint' => 'config',  'callback' => 'fppmatrixscrollerPostConfig'),
        array('method' => 'POST', 'endpoint' => 'message',     'callback' => 'fppmatrixscrollerMessage'),
        array('method' => 'POST', 'endpoint' => 'message/all', 'callback' => 'fppmatrixscrollerMessageAll'),
        array('method' => 'POST', 'endpoint' => 'output',      'callback' => 'fppmatrixscrollerOutput'),
        array('method' => 'POST', 'endpoint' => 'reload',      'callback' => 'fppmatrixscrollerReload'),
        array('method' => 'GET',  'endpoint' => 'fonts',          'callback' => 'fppmatrixscrollerFonts'),
        array('method' => 'GET',  'endpoint' => 'music',          'callback' => 'fppmatrixscrollerMusic'),
        array('method' => 'GET',  'endpoint' => 'daemon/start',   'callback' => 'fppmatrixscrollerDaemonStart'),
        array('method' => 'POST', 'endpoint' => 'daemon/stop',    'callback' => 'fppmatrixscrollerDaemonStop'),
        array('method' => 'POST', 'endpoint' => 'daemon/restart', 'callback' => 'fppmatrixscrollerDaemonRestart'),
        array('method' => 'GET',  'endpoint' => 'backups',              'callback' => 'fppmatrixscrollerBackups'),
        array('method' => 'POST', 'endpoint' => 'backup',              'callback' => 'fppmatrixscrollerBackup'),
        array('method' => 'POST', 'endpoint' => 'restore',             'callback' => 'fppmatrixscrollerRestore'),
        array('method' => 'GET',  'endpoint' => 'backup/download',     'callback' => 'fppmatrixscrollerBackupDownload'),
        array('method' => 'POST', 'endpoint' => 'backup/delete',       'callback' => 'fppmatrixscrollerBackupDelete'),
        array('method' => 'POST', 'endpoint' => 'backup/delete-all',   'callback' => 'fppmatrixscrollerBackupDeleteAll'),
    );

    foreach ($eps as $ep) {
        array_push($result, $ep);
    }

    return $result;
}

function fppmatrixscrollerDaemonRequest($path, $method = 'GET') {
    $daemon_url = 'http://localhost:32329/api/plugin/matrixscroller/' . $path;
    $opts = array(
        'http' => array(
            'method'        => $method,
            'timeout'       => 5,
            'ignore_errors' => true,
        )
    );
    if ($method === 'POST') {
        $body = file_get_contents('php://input');
        if ($body !== false && $body !== '') {
            $opts['http']['header']  = "Content-Type: application/json\r\n";
            $opts['http']['content'] = $body;
        }
    }
    $ctx  = stream_context_create($opts);
    $resp = @file_get_contents($daemon_url, false, $ctx);
    if ($resp === false) {
        return json(array('error' => 'matrixscroller daemon not running'));
    }
    $data = json_decode($resp, true);
    if ($data === null) {
        return json(array('error' => 'invalid response from daemon'));
    }
    return json($data);
}

function fppmatrixscrollerFonts() {
    $resp = @file_get_contents('http://localhost/api/overlays/fonts');
    if ($resp === false) return json(array());
    $data = json_decode($resp, true);
    return json(is_array($data) ? $data : array());
}

function fppmatrixscrollerMusic() {
    $resp = @file_get_contents('http://localhost/api/files/music');
    if ($resp === false) return json(array('files' => array()));
    $data = json_decode($resp, true);
    return json($data ?: array('files' => array()));
}

function fppmatrixscrollerStatus()     { return fppmatrixscrollerDaemonRequest('status'); }
function fppmatrixscrollerGetConfig()  { return fppmatrixscrollerDaemonRequest('config'); }
function fppmatrixscrollerModels()     { return fppmatrixscrollerDaemonRequest('models'); }
function fppmatrixscrollerPostConfig() { return fppmatrixscrollerDaemonRequest('config', 'POST'); }
function fppmatrixscrollerMessage()    { return fppmatrixscrollerDaemonRequest('message', 'POST'); }
function fppmatrixscrollerMessageAll() { return fppmatrixscrollerDaemonRequest('message/all', 'POST'); }
function fppmatrixscrollerOutput()     { return fppmatrixscrollerDaemonRequest('output', 'POST'); }
function fppmatrixscrollerReload()     { return fppmatrixscrollerDaemonRequest('reload', 'POST'); }
function fppmatrixscrollerDaemonStop()    { return fppmatrixscrollerDaemonRequest('daemon/stop', 'POST'); }
function fppmatrixscrollerDaemonRestart() { return fppmatrixscrollerDaemonRequest('daemon/restart', 'POST'); }
function fppmatrixscrollerBackups()         { return fppmatrixscrollerDaemonRequest('backups'); }
function fppmatrixscrollerBackup()          { return fppmatrixscrollerDaemonRequest('backup', 'POST'); }
function fppmatrixscrollerRestore()         { return fppmatrixscrollerDaemonRequest('restore', 'POST'); }
function fppmatrixscrollerBackupDelete()    { return fppmatrixscrollerDaemonRequest('backup/delete', 'POST'); }
function fppmatrixscrollerBackupDeleteAll() { return fppmatrixscrollerDaemonRequest('backup/delete-all', 'POST'); }
function fppmatrixscrollerBackupDownload() {
    $qs = isset($_SERVER['QUERY_STRING']) && $_SERVER['QUERY_STRING'] !== '' ? '?' . $_SERVER['QUERY_STRING'] : '';
    return fppmatrixscrollerDaemonRequest('backup/download' . $qs);
}

function fppmatrixscrollerDaemonStart() {
    $plugin_dir  = '/home/fpp/media/plugins/fpp-matrixscroller';
    $daemon      = $plugin_dir . '/matrixscroller.py';
    $logfile     = '/home/fpp/media/logs/fpp-matrixscroller.log';
    // Check if already responding
    $alive = @file_get_contents('http://localhost:32329/api/plugin/matrixscroller/status');
    if ($alive !== false) {
        return json(array('status' => 'already_running'));
    }
    shell_exec('nohup python3 ' . escapeshellarg($daemon) .
               ' >> ' . escapeshellarg($logfile) . ' 2>&1 </dev/null &');
    usleep(1200000); // 1.2 s startup grace
    $alive = @file_get_contents('http://localhost:32329/api/plugin/matrixscroller/status');
    return json(array('status' => $alive !== false ? 'running' : 'starting'));
}

?>
