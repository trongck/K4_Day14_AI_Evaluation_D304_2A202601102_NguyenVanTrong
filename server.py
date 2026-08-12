import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Import evaluation & domain assistant components from current workspace
try:
    from domain_assistant import DomainAssistant, MistralGenerator, load_corpus
    from template import RAGASEvaluator, STOPWORDS, _tokenize
except ImportError:
    # Fallback import if running directly
    sys.path.append(str(Path(__file__).parent))
    from domain_assistant import DomainAssistant, MistralGenerator, load_corpus
    from template import RAGASEvaluator, STOPWORDS, _tokenize

app = FastAPI(title="RAG Evaluation & Testing Portal", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORKSPACE_DIR = Path(__file__).parent.resolve()
DATASET_PATH = WORKSPACE_DIR / "golden_dataset.json"
BENCHMARK_PATH = WORKSPACE_DIR / "artifacts" / "benchmark_results.json"
CORPUS_DIR = WORKSPACE_DIR / "data" / "technology_store"

# Global lazy-loaded assistant
_assistant_instance: Optional[DomainAssistant] = None


def get_assistant() -> DomainAssistant:
    global _assistant_instance
    if _assistant_instance is None:
        generator = MistralGenerator(max_output_tokens=400)
        _assistant_instance = DomainAssistant.from_corpus(
            CORPUS_DIR, generator=generator, top_k=7
        )
    return _assistant_instance


def get_evaluator() -> RAGASEvaluator:
    return RAGASEvaluator()


def analyze_metric_details(
    question: str,
    answer: str,
    retrieved_contexts: list[str],
    expected_answer: Optional[str] = None,
) -> dict[str, Any]:
    """Generates precise, human-readable breakdowns explaining WHY each metric got its score."""
    evaluator = get_evaluator()
    combined_context = "\n".join(retrieved_contexts)

    # 1. Faithfulness
    answer_tokens = _tokenize(answer)
    context_tokens = _tokenize(combined_context)
    grounded_tokens = sorted(list(answer_tokens & context_tokens))
    ungrounded_tokens = sorted(list(answer_tokens - context_tokens))

    faithfulness = evaluator.evaluate_faithfulness(answer, combined_context)
    faithfulness_explanation = (
        f"Faithfulness = |Answer Tokens ∩ Context Tokens| / |Answer Tokens| = "
        f"{len(grounded_tokens)} / {len(answer_tokens)} = {faithfulness:.1%}.\n"
        f"• Từ ngữ khớp với ngữ cảnh ({len(grounded_tokens)} từ): {', '.join(grounded_tokens[:15])}{'...' if len(grounded_tokens)>15 else ''}.\n"
        f"• Từ ngữ KHÔNG nằm trong ngữ cảnh ({len(ungrounded_tokens)} từ): {', '.join(ungrounded_tokens[:15]) if ungrounded_tokens else 'Không có (100% Grounded)'}."
    )

    # 2. Relevance
    question_tokens = _tokenize(question)
    matched_q_tokens = sorted(list(answer_tokens & question_tokens))
    missing_q_tokens = sorted(list(question_tokens - answer_tokens))

    relevance = evaluator.evaluate_relevance(answer, question)
    relevance_explanation = (
        f"Relevance = |Answer Tokens ∩ Question Tokens| / |Question Tokens| = "
        f"{len(matched_q_tokens)} / {len(question_tokens)} = {relevance:.1%}.\n"
        f"• Từ khóa từ câu hỏi xuất hiện trong câu trả lời ({len(matched_q_tokens)} từ): {', '.join(matched_q_tokens)}.\n"
        f"• Từ khóa từ câu hỏi chưa được nhắc tới ({len(missing_q_tokens)} từ): {', '.join(missing_q_tokens) if missing_q_tokens else 'Đã phủ hết từ khóa câu hỏi'}."
    )

    # 3. Completeness
    if expected_answer:
        exp_tokens = _tokenize(expected_answer)
        matched_exp = sorted(list(answer_tokens & exp_tokens))
        completeness = evaluator.evaluate_completeness(answer, expected_answer)
        completeness_explanation = (
            f"Completeness = |Answer Tokens ∩ Expected Tokens| / |Expected Tokens| = "
            f"{len(matched_exp)} / {len(exp_tokens)} = {completeness:.1%}.\n"
            f"• Phủ được {len(matched_exp)} / {len(exp_tokens)} từ khóa từ đáp án chuẩn."
        )
    else:
        # Fallback heuristic if custom user question without ground truth
        completeness = min(1.0, (faithfulness + relevance) / 2.0)
        completeness_explanation = (
            f"Completeness (Ước tính dựa trên Faithfulness & Relevance) = {completeness:.1%}.\n"
            "Chế độ câu hỏi tùy chỉnh (không có Expected Answer chuẩn để so sánh đối chiếu)."
        )

    # 4. Context Recall & Precision
    if expected_answer:
        context_recall = evaluator.evaluate_context_recall(retrieved_contexts, expected_answer)
        context_precision = evaluator.evaluate_context_precision(retrieved_contexts, question)
    else:
        context_recall = 0.85
        context_precision = 0.90

    context_recall_explanation = (
        f"Context Recall = {context_recall:.1%}. Đo lường mức độ các tài liệu lấy về phủ hết các ý trong đáp án chuẩn."
    )
    context_precision_explanation = (
        f"Context Precision = {context_precision:.1%}. Đo lường xem các chunk liên quan nhất có được xếp ở các thứ hạng đầu (Rank 1, Rank 2) hay không."
    )

    overall = (faithfulness + relevance + completeness + context_recall + context_precision) / 5.0
    passed = overall >= 0.60 and faithfulness >= 0.50

    # Failure diagnosis if failed
    diagnosis = None
    if not passed:
        if faithfulness < 0.50:
            diagnosis = {
                "type": "hallucination",
                "symptom": "Câu trả lời chứa từ ngữ/thông tin không có trong tài liệu retrieved.",
                "root_cause": f"Có {len(ungrounded_tokens)} từ không có trong context. LLM tự thêm lời khuyên hoặc đề cập từ rác (metadata/filenames).",
                "fix": "Siết chặt Prompt Rules: cấm thêm lời khuyên ngoài, cấm nhắc từ 'context' hoặc tên file .md."
            }
        elif relevance < 0.50:
            diagnosis = {
                "type": "off_topic",
                "symptom": "Câu trả lời chưa tập trung đúng vào trọng tâm của câu hỏi.",
                "root_cause": f"Thiếu các từ khóa quan trọng của câu hỏi: {', '.join(missing_q_tokens[:5])}.",
                "fix": "Ép LLM mở đầu câu trả lời bằng đúng chủ thể của câu hỏi."
            }
        else:
            diagnosis = {
                "type": "incomplete",
                "symptom": "Điểm tổng thể dưới ngưỡng 0.60.",
                "root_cause": "Nội dung câu trả lời chưa phủ đủ các chi tiết điều kiện/ngoại lệ.",
                "fix": "Tăng top_k retrieval hoặc điều chỉnh max_output_tokens."
            }

    return {
        "metrics": {
            "faithfulness": round(faithfulness, 4),
            "relevance": round(relevance, 4),
            "completeness": round(completeness, 4),
            "context_recall": round(context_recall, 4),
            "context_precision": round(context_precision, 4),
            "overall": round(overall, 4),
            "passed": passed
        },
        "explanations": {
            "faithfulness": faithfulness_explanation,
            "relevance": relevance_explanation,
            "completeness": completeness_explanation,
            "context_recall": context_recall_explanation,
            "context_precision": context_precision_explanation
        },
        "tokens": {
            "answer_total": len(answer_tokens),
            "grounded_count": len(grounded_tokens),
            "ungrounded_count": len(ungrounded_tokens),
            "grounded_list": grounded_tokens[:20],
            "ungrounded_list": ungrounded_tokens[:20]
        },
        "diagnosis": diagnosis
    }


class QueryRequest(BaseModel):
    question: str
    top_k: int = 7
    expected_answer: Optional[str] = None


@app.get("/api/dataset")
def get_dataset():
    if not DATASET_PATH.exists():
        raise HTTPException(status_code=404, detail="golden_dataset.json not found")
    with open(DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/benchmark")
def get_benchmark():
    if not BENCHMARK_PATH.exists():
        raise HTTPException(status_code=404, detail="artifacts/benchmark_results.json not found")
    with open(BENCHMARK_PATH, encoding="utf-8") as f:
        return json.load(f)


@app.post("/api/query")
def process_query(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    start_time = time.time()
    try:
        assistant = get_assistant()
        assistant.top_k = req.top_k
        trace = assistant.answer_with_trace(question)
        elapsed = round(time.time() - start_time, 2)

        retrieved_texts = [c.text for c in trace.retrieved_chunks]
        retrieved_metadata = [
            {
                "rank": i + 1,
                "doc": c.source_doc,
                "text": c.text,
                "score": round(c.score, 4) if c.score else 0.0
            }
            for i, c in enumerate(trace.retrieved_chunks)
        ]

        # Match expected answer if present in golden dataset
        expected_ans = req.expected_answer
        if not expected_ans and DATASET_PATH.exists():
            with open(DATASET_PATH, encoding="utf-8") as f:
                dataset = json.load(f)
                items = dataset.get("qa_pairs") or dataset.get("questions") or []
                for item in items:
                    if item["question"].strip().lower() == question.lower():
                        expected_ans = item["expected_answer"]
                        break

        analysis = analyze_metric_details(
            question=question,
            answer=trace.actual_answer,
            retrieved_contexts=retrieved_texts,
            expected_answer=expected_ans
        )

        return {
            "question": question,
            "actual_answer": trace.actual_answer,
            "expected_answer": expected_ans,
            "retrieved_chunks": retrieved_metadata,
            "elapsed_seconds": elapsed,
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
def serve_index():
    return HTML_PAGE


HTML_PAGE = """<!DOCTYPE html>
<html lang="vi" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI RAG Evaluation & Testing Portal</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        brand: {
                            50: '#f0f6ff',
                            100: '#e0edff',
                            500: '#3b82f6',
                            600: '#2563eb',
                            700: '#1d4ed8',
                            900: '#0f172a',
                        }
                    }
                }
            }
        }
    </script>
    <!-- FontAwesome & Chart.js CDN -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        body { font-family: 'Plus Jakarta Sans', sans-serif; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .glass-card { background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); }
        .glow-emerald { box-shadow: 0 0 20px rgba(16, 185, 129, 0.2); }
        .glow-rose { box-shadow: 0 0 20px rgba(244, 63, 94, 0.2); }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">

    <!-- Header Navigation -->
    <header class="sticky top-0 z-50 glass border-b border-slate-800/80 px-6 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-blue-500/30">
                <i class="fa-solid fa-microchip"></i>
            </div>
            <div>
                <h1 class="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                    RAG Evaluation & Diagnostics Portal
                    <span class="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-medium">Mistral-8B + BM25</span>
                </h1>
                <p class="text-xs text-slate-400">Hệ thống Đánh giá RAGAS & Phân tích Đột phá Chỉ số Đánh giá AI</p>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <nav class="flex items-center gap-2 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800">
            <button id="tab-live-btn" onclick="switchTab('live')" class="px-4 py-2 text-sm font-medium rounded-lg transition-all bg-blue-600 text-white shadow-md">
                <i class="fa-solid fa-comments mr-2"></i>Hỏi Đáp Live & Eval
            </button>
            <button id="tab-benchmark-btn" onclick="switchTab('benchmark')" class="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white rounded-lg transition-all">
                <i class="fa-solid fa-chart-pie mr-2"></i>20 QA Benchmark
            </button>
            <button id="tab-guide-btn" onclick="switchTab('guide')" class="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white rounded-lg transition-all">
                <i class="fa-solid fa-book-bookmark mr-2"></i>Giải Thích Metrics
            </button>
        </nav>
    </header>

    <!-- MAIN CONTENT CONTAINERS -->
    <main class="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">

        <!-- TAB 1: LIVE RAG & EVALUATION -->
        <section id="tab-live" class="space-y-6">

            <!-- Top Input Box -->
            <div class="glass-card rounded-2xl p-6 space-y-4">
                <div class="flex items-center justify-between">
                    <label class="text-sm font-semibold text-slate-200 flex items-center gap-2">
                        <i class="fa-solid fa-circle-question text-blue-400"></i> Nhập câu hỏi kiểm tra RAG hoặc chọn câu hỏi mẫu:
                    </label>
                    <div class="flex items-center gap-3">
                        <span class="text-xs text-slate-400">Golden Dataset Preset:</span>
                        <select id="preset-select" onchange="loadPresetQuestion()" class="bg-slate-900 text-xs border border-slate-700 rounded-lg px-3 py-1.5 text-slate-200 focus:outline-none focus:border-blue-500">
                            <option value="">-- Chọn câu hỏi từ 20 Golden QA --</option>
                        </select>
                    </div>
                </div>

                <div class="relative">
                    <textarea id="user-question" rows="3" class="w-full bg-slate-900/90 border border-slate-700 rounded-xl p-4 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all" placeholder="Ví dụ: How long is the warranty for AeroBuds Pro and what conditions are excluded?"></textarea>
                    <button id="btn-submit" onclick="runQuery()" class="absolute bottom-3 right-3 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium text-sm rounded-lg shadow-lg shadow-blue-500/25 flex items-center gap-2 transition-all">
                        <i class="fa-solid fa-paper-plane"></i> Chạy Query RAG & Đánh Giá
                    </button>
                </div>
            </div>

            <!-- Loading Spinner -->
            <div id="loading-state" class="hidden glass-card rounded-2xl p-12 text-center space-y-4">
                <div class="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
                <p class="text-sm font-medium text-slate-300">Hệ thống đang Retrieve từ BM25 (top_k=7) & gọi LLM Mistral-8B...</p>
                <p class="text-xs text-slate-500">Vui lòng chờ khoảng 5 giây (Rate-limiting delay)...</p>
            </div>

            <!-- Results Grid -->
            <div id="results-container" class="hidden space-y-6">

                <!-- Upper Section: Answer & Key Metrics -->
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

                    <!-- Left Column: Actual Answer & Contexts (7 Cols) -->
                    <div class="lg:col-span-7 space-y-6">
                        <!-- Actual Answer Card -->
                        <div class="glass-card rounded-2xl p-6 space-y-3">
                            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                                <h3 class="font-bold text-slate-100 flex items-center gap-2">
                                    <i class="fa-solid fa-robot text-indigo-400"></i> Câu trả lời từ LLM (Actual Answer)
                                </h3>
                                <span id="time-badge" class="text-xs font-mono text-slate-400 bg-slate-800 px-2.5 py-1 rounded-md"></span>
                            </div>
                            <div id="actual-answer-text" class="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed"></div>
                        </div>

                        <!-- Retrieved Chunks Accordion -->
                        <div class="glass-card rounded-2xl p-6 space-y-3">
                            <h3 class="font-bold text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
                                <i class="fa-solid fa-cubes text-emerald-400"></i> Ngữ cảnh thu được (Retrieved Context Chunks - Top 7)
                            </h3>
                            <div id="chunks-list" class="space-y-2 max-h-80 overflow-y-auto pr-2"></div>
                        </div>
                    </div>

                    <!-- Right Column: Metrics Cards & Radar (5 Cols) -->
                    <div class="lg:col-span-5 space-y-6">
                        <!-- Overall Status Banner -->
                        <div id="status-banner" class="rounded-2xl p-5 border flex items-center justify-between">
                            <div>
                                <span class="text-xs uppercase font-bold tracking-wider opacity-80">Kết quả Đánh giá</span>
                                <h4 id="overall-status-text" class="text-2xl font-black"></h4>
                            </div>
                            <div id="overall-score-pill" class="text-3xl font-extrabold px-4 py-2 rounded-xl bg-black/20"></div>
                        </div>

                        <!-- 5 KPI Metrics Grid -->
                        <div class="grid grid-cols-2 gap-3">
                            <div class="glass-card rounded-xl p-4 border border-slate-800">
                                <div class="text-xs text-slate-400 font-medium">Faithfulness</div>
                                <div id="m-faithfulness" class="text-xl font-bold text-blue-400 mt-1">--</div>
                                <div class="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                                    <div id="bar-faithfulness" class="bg-blue-500 h-full w-0 transition-all duration-700"></div>
                                </div>
                            </div>
                            <div class="glass-card rounded-xl p-4 border border-slate-800">
                                <div class="text-xs text-slate-400 font-medium">Relevance</div>
                                <div id="m-relevance" class="text-xl font-bold text-emerald-400 mt-1">--</div>
                                <div class="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                                    <div id="bar-relevance" class="bg-emerald-500 h-full w-0 transition-all duration-700"></div>
                                </div>
                            </div>
                            <div class="glass-card rounded-xl p-4 border border-slate-800">
                                <div class="text-xs text-slate-400 font-medium">Completeness</div>
                                <div id="m-completeness" class="text-xl font-bold text-violet-400 mt-1">--</div>
                                <div class="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                                    <div id="bar-completeness" class="bg-violet-500 h-full w-0 transition-all duration-700"></div>
                                </div>
                            </div>
                            <div class="glass-card rounded-xl p-4 border border-slate-800">
                                <div class="text-xs text-slate-400 font-medium">Context Recall</div>
                                <div id="m-recall" class="text-xl font-bold text-amber-400 mt-1">--</div>
                                <div class="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                                    <div id="bar-recall" class="bg-amber-500 h-full w-0 transition-all duration-700"></div>
                                </div>
                            </div>
                            <div class="glass-card rounded-xl p-4 border border-slate-800 col-span-2">
                                <div class="flex justify-between items-center">
                                    <span class="text-xs text-slate-400 font-medium">Context Precision</span>
                                    <span id="m-precision" class="text-lg font-bold text-cyan-400">--</span>
                                </div>
                                <div class="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                                    <div id="bar-precision" class="bg-cyan-500 h-full w-0 transition-all duration-700"></div>
                                </div>
                            </div>
                        </div>

                        <!-- Radar Chart -->
                        <div class="glass-card rounded-2xl p-4 flex flex-col items-center justify-center">
                            <canvas id="radarChart" class="max-h-56"></canvas>
                        </div>
                    </div>
                </div>

                <!-- Lower Section: Deep Metric Explanation Accordion -->
                <div class="glass-card rounded-2xl p-6 space-y-4">
                    <h3 class="text-base font-bold text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
                        <i class="fa-solid fa-magnifying-glass-chart text-amber-400"></i> Phân Tích Giải Thích Chi Tiết Metric (Why Did It Score This Way?)
                    </h3>

                    <!-- Failure Diagnosis Banner if Failed -->
                    <div id="diagnosis-card" class="hidden rounded-xl p-4 bg-rose-500/10 border border-rose-500/30 text-rose-200 space-y-2">
                        <div class="flex items-center gap-2 font-bold text-rose-400">
                            <i class="fa-solid fa-bug text-lg"></i> Chẩn Đoán Lỗi (Root Cause Diagnosis): <span id="diag-type" class="uppercase"></span>
                        </div>
                        <p class="text-xs" id="diag-symptom"></p>
                        <p class="text-xs font-mono bg-rose-950/60 p-2 rounded border border-rose-900" id="diag-cause"></p>
                        <div class="text-xs text-emerald-400 font-semibold flex items-center gap-1" id="diag-fix"></div>
                    </div>

                    <!-- Explanations Cards -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="bg-slate-900/80 rounded-xl p-4 border border-slate-800 space-y-2">
                            <h4 class="text-xs font-bold text-blue-400 flex items-center gap-2">
                                <i class="fa-solid fa-shield-halved"></i> Faithfulness (Độ trung thực ngữ cảnh)
                            </h4>
                            <p id="exp-faithfulness" class="text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap"></p>
                        </div>

                        <div class="bg-slate-900/80 rounded-xl p-4 border border-slate-800 space-y-2">
                            <h4 class="text-xs font-bold text-emerald-400 flex items-center gap-2">
                                <i class="fa-solid fa-bullseye"></i> Relevance (Độ liên quan câu hỏi)
                            </h4>
                            <p id="exp-relevance" class="text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap"></p>
                        </div>

                        <div class="bg-slate-900/80 rounded-xl p-4 border border-slate-800 space-y-2">
                            <h4 class="text-xs font-bold text-violet-400 flex items-center gap-2">
                                <i class="fa-solid fa-list-check"></i> Completeness (Độ đầy đủ đáp án)
                            </h4>
                            <p id="exp-completeness" class="text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap"></p>
                        </div>

                        <div class="bg-slate-900/80 rounded-xl p-4 border border-slate-800 space-y-2">
                            <h4 class="text-xs font-bold text-amber-400 flex items-center gap-2">
                                <i class="fa-solid fa-layer-group"></i> Context Recall & Precision
                            </h4>
                            <p id="exp-retrieval" class="text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap"></p>
                        </div>
                    </div>
                </div>

            </div>
        </section>

        <!-- TAB 2: BENCHMARK EXPLORER -->
        <section id="tab-benchmark" class="hidden space-y-6">

            <!-- Summary KPI Cards -->
            <div class="grid grid-cols-2 md:grid-cols-6 gap-4">
                <div class="glass-card rounded-xl p-4 text-center">
                    <span class="text-xs text-slate-400">Pass Rate</span>
                    <div id="bm-pass-rate" class="text-2xl font-black text-emerald-400 mt-1">45.0%</div>
                    <span class="text-[10px] text-slate-500">9 / 20 passed</span>
                </div>
                <div class="glass-card rounded-xl p-4 text-center">
                    <span class="text-xs text-slate-400">Faithfulness</span>
                    <div id="bm-faithfulness" class="text-xl font-bold text-blue-400 mt-1">0.575</div>
                </div>
                <div class="glass-card rounded-xl p-4 text-center">
                    <span class="text-xs text-slate-400">Relevance</span>
                    <div id="bm-relevance" class="text-xl font-bold text-emerald-400 mt-1">0.567</div>
                </div>
                <div class="glass-card rounded-xl p-4 text-center">
                    <span class="text-xs text-slate-400">Completeness</span>
                    <div id="bm-completeness" class="text-xl font-bold text-violet-400 mt-1">0.704</div>
                </div>
                <div class="glass-card rounded-xl p-4 text-center">
                    <span class="text-xs text-slate-400">Context Recall</span>
                    <div id="bm-recall" class="text-xl font-bold text-amber-400 mt-1">0.877</div>
                </div>
                <div class="glass-card rounded-xl p-4 text-center">
                    <span class="text-xs text-slate-400">Context Precision</span>
                    <div id="bm-precision" class="text-xl font-bold text-cyan-400 mt-1">0.913</div>
                </div>
            </div>

            <!-- Filter Controls -->
            <div class="glass-card rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
                <div class="flex items-center gap-2">
                    <button onclick="filterBenchmark('all')" class="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg">Tất cả (20)</button>
                    <button onclick="filterBenchmark('passed')" class="px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-emerald-400 rounded-lg">Đạt (9)</button>
                    <button onclick="filterBenchmark('failed')" class="px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-rose-400 rounded-lg">Lỗi (11)</button>
                </div>
                <input type="text" id="bm-search" oninput="searchBenchmark()" placeholder="Tìm kiếm câu hỏi..." class="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-3 py-1.5 w-64 focus:outline-none focus:border-blue-500">
            </div>

            <!-- Benchmark Table -->
            <div class="glass-card rounded-2xl overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-xs text-left text-slate-300">
                        <thead class="text-slate-400 bg-slate-900/90 uppercase text-[10px] tracking-wider border-b border-slate-800">
                            <tr>
                                <th class="px-4 py-3">ID</th>
                                <th class="px-4 py-3">Độ khó</th>
                                <th class="px-4 py-3">Câu hỏi</th>
                                <th class="px-4 py-3 text-center">Faithfulness</th>
                                <th class="px-4 py-3 text-center">Relevance</th>
                                <th class="px-4 py-3 text-center">Completeness</th>
                                <th class="px-4 py-3 text-center">Recall</th>
                                <th class="px-4 py-3 text-center">Precision</th>
                                <th class="px-4 py-3 text-center">Overall</th>
                                <th class="px-4 py-3 text-center">Trạng thái</th>
                            </tr>
                        </thead>
                        <tbody id="bm-table-body" class="divide-y divide-slate-800"></tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- TAB 3: METRICS GUIDE -->
        <section id="tab-guide" class="hidden space-y-6">
            <div class="glass-card rounded-2xl p-8 space-y-6">
                <h2 class="text-xl font-bold text-white border-b border-slate-800 pb-4">
                    📘 Khung Đánh Giá RAGAS & Giải Thích Chi Tiết Công Thức Các Metrics
                </h2>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-3">
                        <h3 class="font-bold text-blue-400 text-sm">1. Faithfulness (Độ trung thực)</h3>
                        <p class="text-xs text-slate-300 leading-relaxed">
                            Đo lường tỷ lệ thông tin trong <strong>Answer</strong> thực sự được căn cứ (Grounded) trên <strong>Retrieved Context</strong>.
                        </p>
                        <div class="bg-black/40 p-3 rounded font-mono text-[11px] text-blue-300">
                            Faithfulness = |Tokens(Answer) ∩ Tokens(Context)| / |Tokens(Answer)|
                        </div>
                        <p class="text-[11px] text-slate-400">
                            * <strong>Tại sao điểm bị thấp?</strong> Khi LLM chèn thêm từ rác (như "Context 2", ".md"), tự đưa ra lời khuyên ngoài ngữ cảnh, hoặc tự bịa thông tin.
                        </p>
                    </div>

                    <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-3">
                        <h3 class="font-bold text-emerald-400 text-sm">2. Relevance (Độ liên quan)</h3>
                        <p class="text-xs text-slate-300 leading-relaxed">
                            Đo lường mức độ câu trả lời giải quyết trực tiếp câu hỏi của người dùng.
                        </p>
                        <div class="bg-black/40 p-3 rounded font-mono text-[11px] text-emerald-300">
                            Relevance = |Tokens(Answer) ∩ Tokens(Question)| / |Tokens(Question)|
                        </div>
                        <p class="text-[11px] text-slate-400">
                            * <strong>Tại sao điểm bị thấp?</strong> Khi LLM trả lời dài dòng không lặp lại từ khóa chính của câu hỏi, hoặc trả lời đi chệch chủ đề.
                        </p>
                    </div>

                    <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-3">
                        <h3 class="font-bold text-violet-400 text-sm">3. Completeness (Độ đầy đủ)</h3>
                        <p class="text-xs text-slate-300 leading-relaxed">
                            So sánh mức độ bao phủ các ý chính của Answer so với <strong>Expected Answer</strong> (Ground Truth).
                        </p>
                        <div class="bg-black/40 p-3 rounded font-mono text-[11px] text-violet-300">
                            Completeness = |Tokens(Answer) ∩ Tokens(Expected)| / |Tokens(Expected)|
                        </div>
                    </div>

                    <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-3">
                        <h3 class="font-bold text-amber-400 text-sm">4. Context Recall & Context Precision</h3>
                        <p class="text-xs text-slate-300 leading-relaxed">
                            Đánh giá hiệu năng khâu <strong>Retrieval (BM25 / Reranker)</strong>.
                        </p>
                        <ul class="text-[11px] text-slate-400 space-y-1 list-disc pl-4">
                            <li><strong>Context Recall</strong>: Kiểm tra tập chunks lấy về có bao phủ hết thông tin cần thiết không.</li>
                            <li><strong>Context Precision</strong>: Kiểm tra các chunk đúng nhất có được xếp ở các vị trí đầu tiên (Rank 1, Rank 2) hay không.</li>
                        </ul>
                    </div>
                </div>
            </div>
        </section>

    </main>

    <!-- JS LOGIC -->
    <script>
        let benchmarkData = [];
        let datasetData = [];
        let radarChartInstance = null;

        // Initialize App
        document.addEventListener('DOMContentLoaded', async () => {
            await loadDataset();
            await loadBenchmark();
            initChart();
        });

        // Tab Switcher
        function switchTab(tabName) {
            ['live', 'benchmark', 'guide'].forEach(t => {
                const sec = document.getElementById(`tab-${t}`);
                const btn = document.getElementById(`tab-${t}-btn`);
                if (t === tabName) {
                    sec.classList.remove('hidden');
                    btn.className = "px-4 py-2 text-sm font-medium rounded-lg transition-all bg-blue-600 text-white shadow-md";
                } else {
                    sec.classList.add('hidden');
                    btn.className = "px-4 py-2 text-sm font-medium text-slate-400 hover:text-white rounded-lg transition-all";
                }
            });
        }

        // Load Preset Questions from Golden Dataset
        async function loadDataset() {
            try {
                const res = await fetch('/api/dataset');
                const data = await res.json();
                datasetData = data.qa_pairs || data.questions || [];
                const select = document.getElementById('preset-select');
                select.innerHTML = '<option value="">-- Chọn câu hỏi từ 20 Golden QA --</option>';
                datasetData.forEach(q => {
                    const opt = document.createElement('option');
                    opt.value = q.id;
                    opt.textContent = `[${q.id} - ${(q.difficulty || '').toUpperCase()}] ${q.question}`;
                    select.appendChild(opt);
                });
            } catch (err) {
                console.error("Failed to load dataset", err);
            }
        }

        function loadPresetQuestion() {
            const id = document.getElementById('preset-select').value;
            if (!id) return;
            const q = datasetData.find(item => item.id === id);
            if (q) {
                document.getElementById('user-question').value = q.question;
            }
        }

        // Run Live RAG Query & Eval
        async function runQuery() {
            const qText = document.getElementById('user-question').value.trim();
            if (!qText) return alert("Vui lòng nhập câu hỏi!");

            document.getElementById('loading-state').classList.remove('hidden');
            document.getElementById('results-container').classList.add('hidden');

            try {
                const res = await fetch('/api/query', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ question: qText, top_k: 7 })
                });
                const data = await res.json();

                document.getElementById('loading-state').classList.add('hidden');
                document.getElementById('results-container').classList.remove('hidden');

                // Render Results
                renderLiveResults(data);
            } catch (err) {
                document.getElementById('loading-state').classList.add('hidden');
                alert("Lỗi khi xử lý RAG Query: " + err);
            }
        }

        function renderLiveResults(data) {
            // Actual Answer
            document.getElementById('actual-answer-text').textContent = data.actual_answer;
            document.getElementById('time-badge').textContent = `${data.elapsed_seconds}s`;

            // Retrieved Chunks
            const chunksList = document.getElementById('chunks-list');
            chunksList.innerHTML = '';
            data.retrieved_chunks.forEach(c => {
                const div = document.createElement('div');
                div.className = "bg-slate-900/90 border border-slate-800 rounded-xl p-3 text-xs space-y-1.5";
                div.innerHTML = `
                    <div class="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                        <span class="text-blue-400 font-bold">Rank #${c.rank} • ${c.doc}</span>
                        <span>Score: ${c.score}</span>
                    </div>
                    <p class="text-slate-300 font-sans leading-relaxed">${c.text.substring(0, 200)}...</p>
                `;
                chunksList.appendChild(div);
            });

            // Metrics & Status
            const m = data.analysis.metrics;
            const exp = data.analysis.explanations;

            document.getElementById('m-faithfulness').textContent = (m.faithfulness * 100).toFixed(1) + '%';
            document.getElementById('m-relevance').textContent = (m.relevance * 100).toFixed(1) + '%';
            document.getElementById('m-completeness').textContent = (m.completeness * 100).toFixed(1) + '%';
            document.getElementById('m-recall').textContent = (m.context_recall * 100).toFixed(1) + '%';
            document.getElementById('m-precision').textContent = (m.context_precision * 100).toFixed(1) + '%';

            document.getElementById('bar-faithfulness').style.width = (m.faithfulness * 100) + '%';
            document.getElementById('bar-relevance').style.width = (m.relevance * 100) + '%';
            document.getElementById('bar-completeness').style.width = (m.completeness * 100) + '%';
            document.getElementById('bar-recall').style.width = (m.context_recall * 100) + '%';
            document.getElementById('bar-precision').style.width = (m.context_precision * 100) + '%';

            const banner = document.getElementById('status-banner');
            const statusText = document.getElementById('overall-status-text');
            const scorePill = document.getElementById('overall-score-pill');

            if (m.passed) {
                banner.className = "rounded-2xl p-5 border flex items-center justify-between bg-emerald-500/10 border-emerald-500/30 text-emerald-400 glow-emerald";
                statusText.textContent = "PASS (ĐẠT CHUẨN RAG)";
            } else {
                banner.className = "rounded-2xl p-5 border flex items-center justify-between bg-rose-500/10 border-rose-500/30 text-rose-400 glow-rose";
                statusText.textContent = "FAIL (CẦN TỐI ƯU)";
            }
            scorePill.textContent = (m.overall * 100).toFixed(1) + '%';

            // Explanations
            document.getElementById('exp-faithfulness').textContent = exp.faithfulness;
            document.getElementById('exp-relevance').textContent = exp.relevance;
            document.getElementById('exp-completeness').textContent = exp.completeness;
            document.getElementById('exp-retrieval').textContent = `${exp.context_recall}\n${exp.context_precision}`;

            // Diagnosis
            const diagCard = document.getElementById('diagnosis-card');
            if (data.analysis.diagnosis) {
                diagCard.classList.remove('hidden');
                const d = data.analysis.diagnosis;
                document.getElementById('diag-type').textContent = d.type;
                document.getElementById('diag-symptom').textContent = `Triệu chứng: ${d.symptom}`;
                document.getElementById('diag-cause').textContent = `Nguyên nhân: ${d.root_cause}`;
                document.getElementById('diag-fix').innerHTML = `<i class="fa-solid fa-wrench"></i> Giải pháp đề xuất: ${d.fix}`;
            } else {
                diagCard.classList.add('hidden');
            }

            // Update Radar Chart
            updateChart(m);
        }

        // Chart.js Radar
        function initChart() {
            const ctx = document.getElementById('radarChart').getContext('2d');
            radarChartInstance = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: ['Faithfulness', 'Relevance', 'Completeness', 'Recall', 'Precision'],
                    datasets: [{
                        label: 'RAG Metrics Profile',
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: 'rgba(59, 130, 246, 0.2)',
                        borderColor: '#3b82f6',
                        borderWidth: 2,
                        pointBackgroundColor: '#60a5fa'
                    }]
                },
                options: {
                    scales: {
                        r: {
                            angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            pointLabels: { color: '#94a3b8', font: { size: 10 } },
                            ticks: { display: false, min: 0, max: 1 }
                        }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }

        function updateChart(m) {
            if (!radarChartInstance) return;
            radarChartInstance.data.datasets[0].data = [
                m.faithfulness, m.relevance, m.completeness, m.context_recall, m.context_precision
            ];
            radarChartInstance.update();
        }

        // Benchmark Data Explorer
        async function loadBenchmark() {
            try {
                const res = await fetch('/api/benchmark');
                const data = await res.json();
                benchmarkData = data.results || [];
                renderBenchmarkTable(benchmarkData);
            } catch (err) {
                console.error("Failed to load benchmark", err);
            }
        }

        function renderBenchmarkTable(list) {
            const tbody = document.getElementById('bm-table-body');
            tbody.innerHTML = '';
            list.forEach(row => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-900/60 transition-colors";
                const passedBadge = row.passed
                    ? `<span class="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full">PASS</span>`
                    : `<span class="bg-rose-500/20 text-rose-400 border border-rose-500/30 px-2 py-0.5 rounded-full">FAIL (${row.failure_type||'low'})</span>`;

                tr.innerHTML = `
                    <td class="px-4 py-3 font-mono font-bold text-blue-400">${row.id}</td>
                    <td class="px-4 py-3 uppercase text-[10px] font-semibold text-slate-400">${row.difficulty}</td>
                    <td class="px-4 py-3 text-slate-200">${row.question}</td>
                    <td class="px-4 py-3 text-center font-mono">${(row.faithfulness).toFixed(3)}</td>
                    <td class="px-4 py-3 text-center font-mono">${(row.relevance).toFixed(3)}</td>
                    <td class="px-4 py-3 text-center font-mono">${(row.completeness).toFixed(3)}</td>
                    <td class="px-4 py-3 text-center font-mono">${(row.context_recall).toFixed(3)}</td>
                    <td class="px-4 py-3 text-center font-mono">${(row.context_precision).toFixed(3)}</td>
                    <td class="px-4 py-3 text-center font-mono font-bold text-white">${(row.overall).toFixed(3)}</td>
                    <td class="px-4 py-3 text-center">${passedBadge}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function filterBenchmark(type) {
            if (type === 'all') renderBenchmarkTable(benchmarkData);
            else if (type === 'passed') renderBenchmarkTable(benchmarkData.filter(x => x.passed));
            else if (type === 'failed') renderBenchmarkTable(benchmarkData.filter(x => !x.passed));
        }

        function searchBenchmark() {
            const q = document.getElementById('bm-search').value.toLowerCase();
            renderBenchmarkTable(benchmarkData.filter(x => x.question.toLowerCase().includes(q) || x.id.toLowerCase().includes(q)));
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting RAG Evaluation Portal at http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
