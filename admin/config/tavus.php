<?php

return [
    // Reuses the same credentials as the Python runtime / .env.
    'api_key'  => env('TAVUS_API_KEY', ''),
    'base_url' => env('TAVUS_BASE_URL', 'https://tavusapi.com/v2'),
];
