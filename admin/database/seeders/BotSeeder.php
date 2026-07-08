<?php

namespace Database\Seeders;

use App\Models\Bot;
use Illuminate\Database\Seeder;

/**
 * Seeds one example bot. IMPORTANT: the `slug` must match the BOT_ID set in the
 * Python runtime's .env for that deployment, so captured conversations line up
 * with the right bot. Set tavus_persona_id + kb_base_context to enable publish.
 */
class BotSeeder extends Seeder
{
    public function run(): void
    {
        Bot::firstOrCreate(
            ['slug' => 'meridian-01'],   // == BOT_ID in that site's .env
            [
                'name' => 'The Meridian – Lobby',
                'property_name' => 'The Meridian',
                'address' => '1200 Grand Avenue',
                'tavus_persona_id' => env('TAVUS_PERSONA_ID'),
                'tavus_replica_id' => env('TAVUS_REPLICA_ID'),
                'kb_base_context' => 'You are the virtual concierge for The Meridian, a luxury residential building at 1200 Grand Avenue.',
                'active' => true,
            ],
        );
    }
}
