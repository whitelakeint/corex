<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('conversations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('bot_id')->constrained('bots')->cascadeOnDelete();
            $table->string('tavus_conversation_id', 120)->unique();
            $table->string('source', 40)->nullable();     // kiosk | manual
            $table->string('status', 40)->nullable();     // active | ended
            $table->timestamp('started_at')->nullable();
            $table->timestamp('ended_at')->nullable();
            $table->integer('duration_seconds')->nullable();
            $table->longText('raw_transcript')->nullable();
            $table->timestamps();
            $table->index('bot_id');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('conversations');
    }
};
