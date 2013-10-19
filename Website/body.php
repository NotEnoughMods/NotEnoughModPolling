<?php
$json_raw = file_get_contents("./mods.json");
$array = json_decode($json_raw, true);
$modNames = array_keys($array);
echo("<ul>\n");
foreach ($modNames as $mod) {
    echo("<li>".$mod."</li>");
}
echo("</ul>");