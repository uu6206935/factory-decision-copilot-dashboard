from __future__ import annotations

from .config import (
    DEEPSEEK_QUERY_REWRITE,
    DEEPSEEK_SEND_DOCUMENT_TEXT,
    DEEPSEEK_SEND_STRUCTURED_EVIDENCE,
)
from .deepseek import available, chat


def rewrite_retrieval_query(question: str, context_hint: str = "") -> str | None:
    """Create a compact manufacturing-search query with DeepSeek Flash."""
    if not (available() and DEEPSEEK_QUERY_REWRITE):
        return None
    safe_hint = context_hint[:3000] if DEEPSEEK_SEND_STRUCTURED_EVIDENCE else "[structured factory evidence not sent]"
    user = f"""Original user question:\n{question}\n\nKnown structured hints:\n{safe_hint}\n\nReturn one compact Japanese search query only. Include useful synonyms for equipment, defect, process, maintenance and part terms when relevant. Do not answer the question."""
    return chat(
        system="You rewrite manufacturing investigation questions for document retrieval. Return only the search query, no bullets or explanation.",
        user=user,
        thinking=False,
        reasoning_effort="low",
        max_tokens=300,
        temperature=0.0,
    )


def synthesize(question: str, structured_text: str, retrieved_text: str) -> str | None:
    if not available():
        return None

    structured = structured_text if DEEPSEEK_SEND_STRUCTURED_EVIDENCE else "[structured evidence sending disabled]"
    retrieved = retrieved_text if DEEPSEEK_SEND_DOCUMENT_TEXT else "[document text sending disabled]"
    prompt = f"""質問:\n{question}\n\n構造化された定量分析:\n{structured}\n\n検索した関連文書:\n{retrieved}\n\n日本語で、読みやすいMarkdown形式の製造品質調査レポートを作成してください。必ず次の4章に分けてください。\n## 1. 観察事実\n## 2. ランク付けした仮説\n## 3. 次に行うべき確認\n## 4. 継続 vs 停止のトレードオフと推奨行動\n\n仮説ランキングやシナリオ比較は、適切ならMarkdown表を使ってください。重要語句は **太字** にしてください。UIラベルや見出しも日本語にし、英語は設備ID・規格名・技術用語など必要な固有表記だけにしてください。優先度指標を確率と呼ばないでください。根拠不足は明記してください。HTMLは出力せずMarkdownだけを返してください。"""
    return chat(
        system=(
            "あなたは根拠に基づく製造品質調査コパイロットです。回答は日本語のMarkdownで作成してください。 "
            "与えられた根拠だけを使い、測定値・原因・証明を創作しないでください。 "
            "現物確認されるまで仮説は仮説として扱ってください。"
        ),
        user=prompt,
        # The ranking/statistics were already computed deterministically upstream;
        # this call only writes them up, so extended "thinking" + high effort just
        # adds latency without adding insight. Medium effort keeps report quality
        # while cutting typical response time substantially.
        thinking=False,
        reasoning_effort="medium",
        max_tokens=2400,
    )
