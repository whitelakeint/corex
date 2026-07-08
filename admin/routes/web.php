<?php

use App\Http\Controllers\ApprovalController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\KnowledgeAnswerController;
use App\Http\Controllers\UnansweredQuestionController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DashboardController::class, 'index'])->name('dashboard');

// Unanswered-question review
Route::get('/questions', [UnansweredQuestionController::class, 'index'])->name('questions.index');
Route::get('/questions/{question}', [UnansweredQuestionController::class, 'show'])->name('questions.show');
Route::post('/questions/{question}/answer', [KnowledgeAnswerController::class, 'store'])->name('answers.store');

// Approval + publish
Route::get('/approvals', [ApprovalController::class, 'index'])->name('approvals.index');
Route::post('/approvals/{answer}/approve', [ApprovalController::class, 'approve'])->name('approvals.approve');
Route::post('/approvals/{answer}/reject', [ApprovalController::class, 'reject'])->name('approvals.reject');
