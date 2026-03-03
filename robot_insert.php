<?php
require_once("config_db.php");

$data = file_get_contents("php://input");
$json = json_decode($data, true);

$received_at = date('Y-m-d H:i:s');

$end_device_ids = $json['end_device_ids'];
$device_id = $end_device_ids['device_id'];
$application_id = $end_device_ids['application_ids']['application_id'];

// Filtra solo tu dispositivo
if ($device_id !== 'rs485-lb-robot') {
    http_response_code(200);
    echo "IGNORED";
    exit();
}

$uplink_message = $json['uplink_message'];
$decoded_payload = $uplink_message['decoded_payload'] ?? [];

// === DATOS DECODIFICADOS SEGÚN TU PAYLOAD ===
$BatV      = $decoded_payload['BatV'] ?? 0.0;
$latitud   = $decoded_payload['latitud'] ?? 0.0;
$longitud  = $decoded_payload['longitud'] ?? 0.0;
$velocidad = $decoded_payload['velocidad'] ?? 0.0;
$balanceo  = $decoded_payload['balanceo'] ?? 0.0;
$voltaje   = $decoded_payload['voltaje'] ?? 0.0;

// Preparar SQL
$sqlCommand = "
    INSERT INTO Robot (
        device_id, application_id, received_at,
        BatV, latitud, longitud, velocidad, balanceo, voltaje
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
";

if ($stmt = mysqli_prepare($conn, $sqlCommand)) {

    mysqli_stmt_bind_param(
        $stmt,
        'sssdddddd', // s = string, d = double
        $device_id,
        $application_id,
        $received_at,
        $BatV,
        $latitud,
        $longitud,
        $velocidad,
        $balanceo,
        $voltaje
    );

    if (mysqli_stmt_execute($stmt)) {
        echo "1"; 
    } else {
        echo "Error al ejecutar la consulta: " . mysqli_stmt_error($stmt);
    }

    mysqli_stmt_close($stmt);
} else {
    echo "Error al preparar la consulta: " . mysqli_error($conn);
}

mysqli_close($conn);
?>