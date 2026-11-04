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
        array('method' => 'POST', 'endpoint' => 'panel',       'callback' => 'fppmatrixscrollerPanel'),
        array('method' => 'GET',  'endpoint' => 'panels',        'callback' => 'fppmatrixscrollerPanels'),
        array('method' => 'GET',  'endpoint' => 'panel-targets', 'callback' => 'fppmatrixscrollerPanelTargets'),
        array('method' => 'GET',  'endpoint' => 'snapshots',     'callback' => 'fppmatrixscrollerSnapshots'),
        array('method' => 'POST', 'endpoint' => 'reload',      'callback' => 'fppmatrixscrollerReload'),
        array('method' => 'GET',  'endpoint' => 'version',        'callback' => 'fppmatrixscrollerVersion'),
        array('method' => 'GET',  'endpoint' => 'fonts',          'callback' => 'fppmatrixscrollerFonts'),
        array('method' => 'GET',  'endpoint' => 'music',          'callback' => 'fppmatrixscrollerMusic'),
        array('method' => 'GET',  'endpoint' => 'sequences',      'callback' => 'fppmatrixscrollerSequences'),
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

function fppmatrixscrollerVersion() { return fppmatrixscrollerDaemonRequest('version'); }

function fppmatrixscrollerFonts() {
    return fppmatrixscrollerDaemonRequest('fonts');
}

// FPP's file list for a media directory, without the <name>.patch.<offset>
// pieces of an upload still in progress, which can't be played
function fppmatrixscrollerFileList($dir) {
    $resp = @file_get_contents('http://localhost/api/files/' . $dir);
    if ($resp === false) return json(array('files' => array()));
    $data = json_decode($resp, true);
    if (!is_array($data)) return json(array('files' => array()));
    if (isset($data['files']) && is_array($data['files'])) {
        $data['files'] = array_values(array_filter($data['files'], function ($f) {
            return !preg_match('/\.patch\.\d+$/', isset($f['name']) ? $f['name'] : '');
        }));
    }
    return json($data);
}

function fppmatrixscrollerMusic()     { return fppmatrixscrollerFileList('music'); }
function fppmatrixscrollerSequences() { return fppmatrixscrollerFileList('sequences'); }

function fppmatrixscrollerStatus()     { return fppmatrixscrollerDaemonRequest('status'); }
function fppmatrixscrollerGetConfig()  { return fppmatrixscrollerDaemonRequest('config'); }
function fppmatrixscrollerModels()     { return fppmatrixscrollerDaemonRequest('models'); }
function fppmatrixscrollerPostConfig() { return fppmatrixscrollerDaemonRequest('config', 'POST'); }
function fppmatrixscrollerMessage()    { return fppmatrixscrollerDaemonRequest('message', 'POST'); }
function fppmatrixscrollerMessageAll() { return fppmatrixscrollerDaemonRequest('message/all', 'POST'); }
function fppmatrixscrollerOutput()     { return fppmatrixscrollerDaemonRequest('output', 'POST'); }
function fppmatrixscrollerPanel()      { return fppmatrixscrollerDaemonRequest('panel', 'POST'); }
function fppmatrixscrollerPanels()       { return fppmatrixscrollerDaemonRequest('panels'); }
function fppmatrixscrollerPanelTargets() { return fppmatrixscrollerDaemonRequest('panel-targets'); }
function fppmatrixscrollerSnapshots()    { return fppmatrixscrollerDaemonRequest('snapshots'); }
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
    global $settings;
    $plugin_dir  = $settings['pluginDirectory'] . '/fpp-matrixscroller';
    $daemon      = $plugin_dir . '/matrixscroller.py';
    $logfile     = $settings['logDirectory'] . '/plugin-fpp-matrixscroller.log';
    // Check if already responding
    $alive = @file_get_contents('http://localhost:32329/api/plugin/matrixscroller/status');
    if ($alive !== false) {
        return json(array('status' => 'already_running'));
    }
    shell_exec('MEDIADIR=' . escapeshellarg($settings['mediaDirectory']) .
               ' LOGDIR=' . escapeshellarg($settings['logDirectory']) .
               ' nohup python3 ' . escapeshellarg($daemon) .
               ' >> ' . escapeshellarg($logfile) . ' 2>&1 </dev/null &');
    usleep(1200000); // 1.2 s startup grace
    $alive = @file_get_contents('http://localhost:32329/api/plugin/matrixscroller/status');
    return json(array('status' => $alive !== false ? 'running' : 'starting'));
}

?>
