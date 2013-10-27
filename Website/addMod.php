<html>
<head>
    <title>NotEnoughMods: Polling || Add Mod</title>
    <script>
        function AGAX_MODPoll(pollName) {
            if (pollName.length  == 0) {
                return;
			}
			xmlhttp = new XMLHttpRequest();
            xmlhttp.onreadystatechange=function() {
                if (xmlhttp.readyState==4 && xmlhttp.status==200) {
                    document.getElementById("myDiv").innerHTML=xmlhttp.responseText;
                }
            }
            xmlhttp.open("GET","addMod.php?poll="+pollName)
			xmlhttp.send()
        }
    </script>
</head>
<body>
<p>Hello, this is a test for generating entries into mods.json</p>
<form name="input" action="addMod_done.php" method="get">
Mod name: <select name="modName">
<?php
    $json_raw = file_get_contents("./NEM_Cache/1.6.2.json");
    $array = json_decode($json_raw, true);
    ksort($array);
    foreach ($array as $modArray) {
        echo("    <option value=\"".$modArray["name"]."\">".$modArray["name"]."</option>\r\n");
    }
?>
</select><br/>
Parser name: <select name="parser" onchange="AGAX_MODPoll(this.value)>
<?php
    $pollers = file_get_contents("./parsers.json");
    $pollArray = json_decode($pollers, true);
    ksort($pollArray);
    foreach ($pollArray as $pollName => $pollInfo) {
        echo("    <option value=\"".$pollName."\">".$pollName."</option>\r\n");
    }
?>
</select>
<?php
    $poll = $_GET["poll"];
    $newWriting = "\"modName\" : {\r\n";
    if (strlen($poll) > 0) {
        $newWriting = $newWriting."    \"function\" : \"{$poll}\",\r\n    \"active\": true,\r\n";
        $pollers = file_get_contents("./parsers.json");
        $pollArray = json_decode($pollers, true);
        if (count($pollArray[$poll]) > 0) {
            echo("<pre>\r\n");
            foreach ($pollArray[$poll] as $key => $value) {
                
                if (gettype($value) == "array") {
                    $pollArray[$poll][$key] = array();
                    $newWriting = $newWriting."    \"".$key."\" : {\r\n";
                    foreach($value as $childKey => $childValue) {
                        $pollArray[$poll][$key][$childValue] = "tempValue";
                        $newWriting = $newWriting."        \"".$childValue."\" : \"tempValue\",\r\n";
                    }
                    $newWriting = $newWriting."    },\r\n";
                }
            }
            echo("</pre>\r\n");
            print_r($pollArray[$poll]);
        }
    }
    $newWriting = $newWriting."},\r\n";
    echo("<pre>\r\n".$newWriting."\r\n</pre>");
?>
</form>
</body>
</html>