<?php

namespace App\Services;

use App\Models\Bot;
use App\Models\KnowledgeAnswer;
use Illuminate\Support\Facades\Http;

/**
 * Publishes a bot's curated knowledge base to its Tavus persona.
 *
 * We REBUILD the whole persona context (base + every published Q&A) and PATCH
 * /context — mirroring scripts/update_persona_context.py. Rebuilding (rather
 * than appending) is idempotent: re-publishing never duplicates entries.
 */
class TavusPublisher
{
    public function publish(Bot $bot): array
    {
        if (empty($bot->tavus_persona_id)) {
            return ['ok' => false, 'error' => 'Bot has no tavus_persona_id configured'];
        }

        $context = $this->buildContext($bot);

        $response = Http::withHeaders([
            'x-api-key' => config('tavus.api_key'),
            'Content-Type' => 'application/json',
        ])->patch(
            rtrim(config('tavus.base_url'), '/') . '/personas/' . $bot->tavus_persona_id,
            [
                ['op' => 'replace', 'path' => '/context', 'value' => $context],
            ]
        );

        if ($response->failed()) {
            return ['ok' => false, 'error' => 'Tavus API ' . $response->status() . ': ' . $response->body()];
        }

        return ['ok' => true, 'context_length' => strlen($context)];
    }

    /**
     * Full persona context = the bot's base context + all published Q&A pairs.
     */
    public function buildContext(Bot $bot): string
    {
        $base = trim((string) $bot->kb_base_context);

        $entries = KnowledgeAnswer::where('bot_id', $bot->id)
            ->where('status', 'published')
            ->orderBy('id')
            ->get();

        if ($entries->isEmpty()) {
            return $base;
        }

        $lines = ["", str_repeat('=', 40), "CURATED Q&A (approved by staff)", str_repeat('=', 40)];
        foreach ($entries as $entry) {
            $lines[] = "";
            $lines[] = "Q: " . trim($entry->question);
            $lines[] = "A: " . trim($entry->answer);
        }

        return trim($base . "\n" . implode("\n", $lines));
    }
}
