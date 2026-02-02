<?php

class User
{
    public function greet()
    {
        echo "Hello";
    }
}

function logMsg($msg)
{
    echo $msg;
}

$u = new User();
$u->greet();
logMsg("test");
