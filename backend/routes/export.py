"""Excel export route endpoint generating styled, in-memory .xlsx files with zero disk footprint."""

import io
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from backend.auth import verify_token, get_uid
from backend.services.user_service import get_firestore_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])

HEADER_COLUMNS = [
    "Journal ID",
    "Date",
    "Mode",
    "Title",
    "Mood Score",
    "Topic",
    "Key Insights",
    "Action Items",
    "Created At",
]


def build_excel_workbook(entries: List[Dict[str, Any]]) -> io.BytesIO:
    """Build and style an in-memory openpyxl Workbook from journal documents."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Journal Reflections"

    # Ensure grid lines are visible
    ws.views.sheetView[0].showGridLines = True

    # Dark-themed modern header styling
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_border = Border(
        bottom=Side(style="medium", color="3B82F6"),
        top=Side(style="thin", color="334155"),
        left=Side(style="thin", color="334155"),
        right=Side(style="thin", color="334155"),
    )

    ws.append(HEADER_COLUMNS)

    for col_num in range(1, len(HEADER_COLUMNS) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = header_border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Style data rows
    regular_font = Font(name="Arial", size=10, color="0F172A")
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    thin_border = Border(
        bottom=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
    )

    for row_idx, entry in enumerate(entries, start=2):
        summary_dict = entry.get("summary") or {}
        insights = summary_dict.get("key_insights", [])
        actions = summary_dict.get("action_items", [])
        insights_str = "\n".join(f"• {i}" for i in insights) if isinstance(insights, list) and insights else str(insights or "")
        actions_str = "\n".join(f"• {a}" for a in actions) if isinstance(actions, list) and actions else str(actions or "")

        mood_score = summary_dict.get("mood_score")
        if mood_score is not None:
            try:
                mood_score = float(mood_score)
            except (ValueError, TypeError):
                pass

        row_values = [
            entry.get("id", "") or entry.get("journalId", ""),
            entry.get("date", ""),
            entry.get("mode", "FreeWrite"),
            entry.get("title") or summary_dict.get("title") or "Journal Reflection",
            mood_score if mood_score is not None else "",
            summary_dict.get("topic", ""),
            insights_str,
            actions_str,
            entry.get("createdAt", ""),
        ]
        ws.append(row_values)

        # Apply cell styling
        for col_num in range(1, len(HEADER_COLUMNS) + 1):
            cell = ws.cell(row=row_idx, column=col_num)
            cell.font = regular_font
            cell.border = thin_border
            if row_idx % 2 == 1:
                cell.fill = alt_fill

            if col_num in (1, 2, 3, 5, 9):
                cell.alignment = Alignment(horizontal="center", vertical="top")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    # Auto-calculate column widths
    min_widths = {1: 16, 2: 14, 3: 16, 4: 28, 5: 14, 6: 22, 7: 35, 8: 30, 9: 24}
    for col_idx in range(1, len(HEADER_COLUMNS) + 1):
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = min_widths.get(col_idx, 20)

    # Save to in-memory bytes buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


@router.get("", response_class=StreamingResponse)
async def export_journals_excel(
    range: str = Query("all", description="Date range for export: 'weekly', 'monthly', or 'all'"),
    current_user: Any = Depends(verify_token),
) -> StreamingResponse:
    """Generate and stream an in-memory .xlsx workbook of the user's journal entries."""
    uid = get_uid(current_user)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing uid in auth token",
        )

    range_clean = range.strip().lower()
    if range_clean not in ("weekly", "monthly", "all"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid range parameter. Expected 'weekly', 'monthly', or 'all'",
        )

    db = get_firestore_client()
    journals_ref = db.collection("users").document(uid).collection("journals")
    docs = journals_ref.order_by("createdAt", direction="DESCENDING").limit(500).stream()

    entries = []
    now = datetime.now(timezone.utc)

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        if range_clean == "weekly":
            created_at_str = data.get("createdAt")
            if created_at_str:
                try:
                    dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    if (now - dt) > timedelta(days=7):
                        continue
                except ValueError:
                    pass
        elif range_clean == "monthly":
            created_at_str = data.get("createdAt")
            if created_at_str:
                try:
                    dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    if (now - dt) > timedelta(days=30):
                        continue
                except ValueError:
                    pass

        entries.append(data)

    excel_buffer = build_excel_workbook(entries)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"journal_export_{range_clean}_{today_str}.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )
