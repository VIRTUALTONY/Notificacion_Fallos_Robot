<?php
define('TIMEZONE', 'America/Guayaquil');
date_default_timezone_set(TIMEZONE);

define("DB_HOST", "localhost");
define("DB_USER", "xibernetiq");
define("DB_PASSWORD", "Automatica0123@");
define("DB_DATABASE", "Robot");

$conn = new mysqli(DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE);

if ($conn->connect_error) {
    echo "Failure";
    die("Connection failed: " . $conn->connect_error);
} else {
    echo "Connected successfully";
}
?>