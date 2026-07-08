<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * A "bot" is one deployed assistant instance, tied to a property/site. The
 * Python runtime tags every conversation with the bot's slug (BOT_ID) so we can
 * tell which bot had a problem. persona_id + kb_base_context drive publishing.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('bots', function (Blueprint $table) {
            $table->id();
            $table->string('slug', 120)->unique();      // matches BOT_ID in the runtime .env
            $table->string('name', 190);
            $table->string('property_name', 190)->nullable();
            $table->string('address')->nullable();
            $table->string('tavus_persona_id', 120)->nullable();
            $table->string('tavus_replica_id', 120)->nullable();
            $table->longText('kb_base_context')->nullable(); // base persona context; approved Q&A is appended
            $table->boolean('active')->default(true);
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('bots');
    }
};
