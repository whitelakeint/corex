<?php

namespace Database\Seeders;

use App\Models\DeflectionPhrase;
use Illuminate\Database\Seeder;

/**
 * Global "the bot couldn't answer" signals. Kept in sync with
 * backend/transcripts.py::DEFAULT_DEFLECTION_PHRASES and the escalation phrases
 * in scripts/setup_persona.py. Experts can add/disable rows per bot in the UI.
 */
class DeflectionPhraseSeeder extends Seeder
{
    public function run(): void
    {
        $phrases = [
            'a member of our team would be better suited',
            'let me connect you with someone',
            "i've set up a video call",
            'connect you to a real person',
            'connecting you to a staff member',
            "i'm not sure",
            'i am not sure',
            "i don't have that information",
            'i do not have that information',
            "i don't know",
            "i'm not able to help with that",
            "i can't help with that",
            "i'm unable to help with that",
        ];

        foreach ($phrases as $phrase) {
            DeflectionPhrase::firstOrCreate(
                ['bot_id' => null, 'phrase' => $phrase],
                ['match_type' => 'contains', 'active' => true],
            );
        }
    }
}
