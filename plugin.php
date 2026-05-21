<?php
/**
 * fpp-matrixscroller plugin.php
 * Registers plugin REST API routes with FPP and provides the config UI page.
 */

// Register custom API routes with FPP
function matrixscroller_api_routes() {
    return [
        ['GET',  'plugin/matrixscroller/status',  'matrixscroller_proxy'],
        ['GET',  'plugin/matrixscroller/config',  'matrixscroller_proxy'],
        ['GET',  'plugin/matrixscroller/models',  'matrixscroller_proxy'],
        ['POST', 'plugin/matrixscroller/config',  'matrixscroller_proxy'],
        ['POST', 'plugin/matrixscroller/message', 'matrixscroller_proxy'],
        ['POST', 'plugin/matrixscroller/reload',  'matrixscroller_proxy'],
    ];
}

/**
 * Proxy requests to the Python daemon running on port 32329
 */
function matrixscroller_proxy($params = [], $data = null) {
    $method     = $_SERVER['REQUEST_METHOD'];
    $uri        = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
    $daemon_url = 'http://localhost:32329' . $uri;

    $opts = [
        'http' => [
            'method'        => $method,
            'timeout'       => 5,
            'ignore_errors' => true,
        ]
    ];

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
        header('Content-Type: application/json');
        http_response_code(503);
        echo json_encode(['error' => 'matrixscroller daemon not running']);
        return;
    }

    header('Content-Type: application/json');
    echo $resp;
}

// FPP calls GetPluginAPIRoutes() to discover routes
function GetPluginAPIRoutes() {
    return matrixscroller_api_routes();
}
?>
