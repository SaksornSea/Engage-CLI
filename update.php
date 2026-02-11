<?php
// 1. Define your array (or object) in PHP
$version = "1.3";

// 2. Set the content type header.
// This tells Python (and the browser) that the response is plain text.
header('Content-Type: text/plain');

// 3. Output the version string and nothing else!
echo $version;

// Ensure nothing else gets printed
exit();
?>
