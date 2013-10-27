<?php
$json_raw = file_get_contents("./mods.json");
$array = json_decode($json_raw, true);
ksort($array);
echo("<ol>\r\n");
foreach ($array as $mod => $modArray) {
    echo("    <li>".$mod."</li>\r\n");
}
echo("</ol>\r\n");