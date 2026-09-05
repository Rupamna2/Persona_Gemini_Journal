"""Excel export route generating in-memory .xlsx workbooks of user journal history."""

import io
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from google.cloud import firestore
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from backend.auth import verify_token
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


def _parse_iso_date(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        if val.endswith("Z"):
            val = val[:-1] + "+00:00"
        return datetime.fromisoformat(val)
    except Exception:
        return None


def generate_journal_workbook(entries: list[Dict[str, Any]]) -> io.BytesIO:
    """Build an in-memory openpyxl Workbook populated with journal entries."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Personal Reflections"

    # Ensure grid lines are visible
    ws.views.sheetView[0].showGridLines = True

    # Styling definitions
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    data_font = Font(name="Calibri", size=10)
    data_alignment = Alignment(vertical="top", wrap_text=True)
    center_alignment = Alignment(horizontal="center", vertical="top")

    thin_border_side = Side(border_style="thin", color="E2E8F0")
    border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    # 1. Write Header Row
    ws.append(HEADER_COLUMNS)
    ws.row_dimensions[1].height = 28

    for col_num in range(1, len(HEADER_COLUMNS) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = border

    # 2. Write Data Rows
    for row_idx, entry in enumerate(entries, start=2):
        summary_dict = entry.get("summary", {}) or {}
        insights = summary_dict.get("key_insights", [])
        actions = summary_dict.get("action_items", [])
        insights_str = "\n".join(f"• {i}" for i in insights) if insights else ""
        actions_str = "\n".join(f"• {a}" for a in actions) if actions else ""

        mood_score = summary_dict.get("mood_score")
        if mood_score is not None:
            try:
                mood_score = float(mood_score)
            except (ValueError, TypeError):
                pass

        row_values = [
            entry.get("journalId", ""),
            entry.get("date", ""),
            entry.get("mode", ""),
            entry.get("title", "Journal Reflection"),
            mood_score if mood_score is not None else "",
            summary_dict.get("topic", ""),
            insights_str,
            actions_str,
            entry.get("createdAt", ""),
        ]

        ws.append(row_values)
        ws.row_dimensions[row_idx].height = 22 if not (insights_str or actions_str) else 36

        for col_num in range(1, len(row_values) + 1):
            cell = ws.cell(row=row_idx, column=col_num)
            cell.font = data_font
            cell.border = border
            if col_num in (2, 3, 5):  # Date, Mode, Score
                cell.alignment = center_alignment
            else:
                cell.alignment = data_alignment

    # 3. Column Width Auto-Fitting
    min_widths = {1: 16, 2: 14, 3: 16, 4: 28, 5: 14, 6: 22, 7: 35, 8: 30, 9: 24}
    for col_idx in range(1, len(HEADER_COLUMNS) + 1):
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = min_widths.get(col_idx, 20)

    # 4. Stream to in-memory bytes buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


@router.get("", response_class=StreamingResponse)
async def export_journals_excel(
    range: str = Query("all", description="Date range for export: 'weekly', 'monthly', or 'all'"),
    current_user: Dict[str, Any] = Depends(verify_token),
) -> StreamingResponse:
    """Generate and stream an in-memory .xlsx workbook of the user's journal entries."""
    uid = current_user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing uid in auth token",
        )

    range_clean = range.strip().lower()
    if range_clean not in ("weekly", "monthly", "all"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid range parameter. Expected 'weekly', 'monthly', or 'all'.",
        )

    db = get_firestore_client()
    now_utc = datetime.now(timezone.utc)

    # 1. Fetch user's journals
    try:
        journals_ref = db.collection("users").document(uid).collection("journals")
        query = journals_ref.order_by("createdAt", direction=firestore.Query.DESCENDING)
        docs = list(query.stream())
    except Exception as exc:
        logger.error(f"Failed to fetch journals for export (user: {uid}): {exc}")
        docs = []

    # 2. Filter entries by requested time range
    filtered_entries = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["journalId"] = data.get("journalId", doc.id)

        if range_clean == "all":
            filtered_entries.append(data)
            continue

        created_dt = _parse_iso_date(data.get("createdAt"))
        if not created_dt:
            # Fall back to date string check or include
            filtered_entries.append(data)
            continue

        if range_clean == "weekly":
            if created_dt >= now_utc - timedelta(days=7):
                filtered_entries.append(data)
        elif range_clean == "monthly":
            if created_dt >= now_utc - timedelta(days=30):
                filtered_entries.append(data)

    # 3. Generate in-memory Excel workbook stream
    buffer = generate_journal_workbook(filtered_entries)

    filename_date = now_utc.strftime("%Y%m%d")
    filename = f"gemini_journal_export_{range_clean}_{filename_date}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
