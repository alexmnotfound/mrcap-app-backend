from psycopg2.extras import RealDictCursor
from collections import defaultdict
from decimal import Decimal
from app.database import get_db
from app.models import (
    AppUser,
    AppUserCreate,
    AppUserUpdate,
    Account,
    AccountCreate,
    CashMovement,
    CashMovementCreate,
    FundShareMovement,
    FundShareMovementCreate,
    UserMovement,
    AccountSummary,
    FundPosition,
    FundPerformance,
    FundNavPoint,
    MovementReportRow,
)
from typing import List, Optional, Dict


class UserRepository:
    @staticmethod
    def find_all() -> List[AppUser]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM app_users ORDER BY created_at DESC"
                )
                rows = cur.fetchall()
                return [AppUser(**dict(row)) for row in rows]

    @staticmethod
    def find_by_id(user_id: int) -> Optional[AppUser]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM app_users WHERE id = %s",
                    (user_id,)
                )
                row = cur.fetchone()
                return AppUser(**dict(row)) if row else None

    @staticmethod
    def find_by_firebase_uid(firebase_uid: str) -> Optional[AppUser]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM app_users WHERE firebase_uid = %s",
                    (firebase_uid,)
                )
                row = cur.fetchone()
                return AppUser(**dict(row)) if row else None

    @staticmethod
    def find_by_email(email: str) -> Optional[AppUser]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM app_users WHERE email = %s",
                    (email,)
                )
                row = cur.fetchone()
                return AppUser(**dict(row)) if row else None

    @staticmethod
    def create(user_data: AppUserCreate) -> AppUser:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO app_users (firebase_uid, email, full_name, is_admin, status)
                       VALUES (%s, %s, %s, %s, %s)
                       RETURNING *""",
                    (
                        user_data.firebase_uid,
                        user_data.email,
                        user_data.full_name,
                        user_data.is_admin,
                        user_data.status,
                    )
                )
                row = cur.fetchone()
                return AppUser(**dict(row))

    @staticmethod
    def update(user_id: int, user_data: AppUserUpdate) -> Optional[AppUser]:
        updates = []
        values = []
        
        if user_data.email is not None:
            updates.append("email = %s")
            values.append(user_data.email)
        if user_data.full_name is not None:
            updates.append("full_name = %s")
            values.append(user_data.full_name)
        if user_data.is_admin is not None:
            updates.append("is_admin = %s")
            values.append(user_data.is_admin)
        if user_data.status is not None:
            updates.append("status = %s")
            values.append(user_data.status)

        if not updates:
            return UserRepository.find_by_id(user_id)

        values.append(user_id)
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"UPDATE app_users SET {', '.join(updates)} WHERE id = %s RETURNING *",
                    values
                )
                row = cur.fetchone()
                return AppUser(**dict(row)) if row else None

    @staticmethod
    def delete(user_id: int) -> bool:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM app_users WHERE id = %s", (user_id,))
                return cur.rowcount > 0


class AccountRepository:
    @staticmethod
    def find_by_user_id(user_id: int) -> List[Account]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM accounts WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
                rows = cur.fetchall()
                return [Account(**dict(row)) for row in rows]

    @staticmethod
    def find_by_id(account_id: int) -> Optional[Account]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM accounts WHERE id = %s",
                    (account_id,)
                )
                row = cur.fetchone()
                return Account(**dict(row)) if row else None

    @staticmethod
    def create(account_data: AccountCreate) -> Account:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO accounts (user_id, account_number) VALUES (%s, %s) RETURNING *",
                    (account_data.user_id, account_data.account_number)
                )
                row = cur.fetchone()
                return Account(**dict(row))

    @staticmethod
    def get_account_summaries_by_user(user_id: int) -> List[AccountSummary]:
        return AccountRepository._get_account_summaries(filter_user_id=user_id)

    @staticmethod
    def get_account_summaries_for_admin() -> List[AccountSummary]:
        return AccountRepository._get_account_summaries(filter_user_id=None)

    @staticmethod
    def _get_account_summaries(filter_user_id: Optional[int] = None) -> List[AccountSummary]:
        where_conditions = []
        params: List = []
        if filter_user_id is not None:
            where_conditions.append("a.user_id = %s")
            params.append(filter_user_id)
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT 
                        a.id AS account_id,
                        a.account_number,
                        u.full_name,
                        u.email,
                        COALESCE(SUM(CASE WHEN cm.type = 'deposit' THEN cm.amount ELSE 0 END), 0) AS total_deposits,
                        COALESCE(SUM(CASE WHEN cm.type = 'withdrawal' THEN cm.amount ELSE 0 END), 0) AS total_withdrawals,
                        COALESCE(SUM(CASE WHEN cm.type = 'fee' THEN cm.amount ELSE 0 END), 0) AS total_fees
                    FROM accounts a
                    JOIN app_users u ON a.user_id = u.id
                    LEFT JOIN cash_movements cm ON cm.account_id = a.id
                    {where_clause}
                    GROUP BY a.id, a.account_number, u.full_name, u.email
                    ORDER BY u.full_name, a.account_number
                    """,
                    params,
                )
                account_rows = cur.fetchall()

                # Fetch fund positions
                positions_map: Dict[int, List[FundPosition]] = defaultdict(list)
                if account_rows:
                    cur.execute(
                        f"""
                        WITH position_data AS (
                            SELECT 
                                a.id AS account_id,
                                f.id AS fund_id,
                                f.name AS fund_name,
                                f.currency,
                                SUM(
                                    CASE 
                                        WHEN fsm.type = 'subscription' THEN fsm.shares_change
                                        WHEN fsm.type = 'redemption' THEN -fsm.shares_change
                                        ELSE 0
                                    END
                                ) AS total_shares
                            FROM accounts a
                            JOIN app_users u ON a.user_id = u.id
                            JOIN fund_share_movements fsm ON fsm.account_id = a.id
                            JOIN funds f ON f.id = fsm.fund_id
                            {where_clause}
                            GROUP BY a.id, f.id, f.name, f.currency
                        )
                        SELECT * FROM position_data
                        WHERE total_shares <> 0
                        ORDER BY account_id, fund_name
                        """,
                        params,
                    )
                    for pos_row in cur.fetchall():
                        positions_map[pos_row["account_id"]].append(pos_row)

                # Latest NAV per fund
                cur.execute(
                    """
                    SELECT DISTINCT ON (fund_id)
                        fund_id,
                        nav_per_share,
                        total_aum,
                        as_of_date
                    FROM fund_navs
                    ORDER BY fund_id, as_of_date DESC
                    """
                )
                nav_rows = cur.fetchall()
                nav_map = {row["fund_id"]: row for row in nav_rows}

        summaries: List[AccountSummary] = []
        for row in account_rows:
            total_deposits = row["total_deposits"] or Decimal("0")
            total_withdrawals = row["total_withdrawals"] or Decimal("0")
            total_fees = row["total_fees"] or Decimal("0")
            net_invested = total_deposits - total_withdrawals - total_fees

            positions: List[FundPosition] = []
            for pos in positions_map.get(row["account_id"], []):
                total_shares = pos["total_shares"] or Decimal("0")
                latest_nav = nav_map.get(pos["fund_id"])
                latest_nav_value = latest_nav["nav_per_share"] if latest_nav else None
                market_value = None
                if latest_nav_value is not None:
                    market_value = Decimal(total_shares) * Decimal(latest_nav_value)

                positions.append(
                    FundPosition(
                        fund_id=pos["fund_id"],
                        fund_name=pos["fund_name"],
                        currency=pos["currency"],
                        total_shares=total_shares,
                        latest_nav_per_share=latest_nav_value,
                        market_value=market_value,
                    )
                )

            summaries.append(
                AccountSummary(
                    account_id=row["account_id"],
                    account_number=row["account_number"],
                    total_deposits=total_deposits,
                    total_withdrawals=total_withdrawals,
                    total_fees=total_fees,
                    net_invested=net_invested,
                    positions=positions,
                    user_full_name=row["full_name"],
                    user_email=row["email"],
                )
            )

        return summaries


class MovementRepository:
    @staticmethod
    def get_cash_movements_by_account(account_id: int) -> List[CashMovement]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM cash_movements 
                       WHERE account_id = %s 
                       ORDER BY effective_date DESC, created_at DESC""",
                    (account_id,)
                )
                rows = cur.fetchall()
                return [CashMovement(**dict(row)) for row in rows]

    @staticmethod
    def get_cash_movements_by_user(user_id: int) -> List[CashMovement]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT cm.* FROM cash_movements cm
                       JOIN accounts a ON cm.account_id = a.id
                       WHERE a.user_id = %s
                       ORDER BY cm.effective_date DESC, cm.created_at DESC""",
                    (user_id,)
                )
                rows = cur.fetchall()
                return [CashMovement(**dict(row)) for row in rows]

    @staticmethod
    def create_cash_movement(movement_data: CashMovementCreate) -> CashMovement:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO cash_movements 
                       (account_id, type, amount, currency, effective_date)
                       VALUES (%s, %s, %s, %s, %s)
                       RETURNING *""",
                    (
                        movement_data.account_id,
                        movement_data.type,
                        movement_data.amount,
                        movement_data.currency,
                        movement_data.effective_date,
                    )
                )
                row = cur.fetchone()
                return CashMovement(**dict(row))

    @staticmethod
    def get_fund_share_movements_by_account(account_id: int) -> List[FundShareMovement]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT fsm.* FROM fund_share_movements fsm
                       WHERE fsm.account_id = %s
                       ORDER BY fsm.effective_date DESC, fsm.created_at DESC""",
                    (account_id,)
                )
                rows = cur.fetchall()
                return [FundShareMovement(**dict(row)) for row in rows]

    @staticmethod
    def get_fund_share_movements_by_user(user_id: int) -> List[FundShareMovement]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT fsm.* FROM fund_share_movements fsm
                       JOIN accounts a ON fsm.account_id = a.id
                       WHERE a.user_id = %s
                       ORDER BY fsm.effective_date DESC, fsm.created_at DESC""",
                    (user_id,)
                )
                rows = cur.fetchall()
                return [FundShareMovement(**dict(row)) for row in rows]

    @staticmethod
    def create_fund_share_movement(movement_data: FundShareMovementCreate) -> FundShareMovement:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO fund_share_movements 
                       (account_id, fund_id, cash_movement_id, type, shares_change, share_price, total_amount, effective_date)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING *""",
                    (
                        movement_data.account_id,
                        movement_data.fund_id,
                        movement_data.cash_movement_id,
                        movement_data.type,
                        movement_data.shares_change,
                        movement_data.share_price,
                        movement_data.total_amount,
                        movement_data.effective_date,
                    )
                )
                row = cur.fetchone()
                return FundShareMovement(**dict(row))

    @staticmethod
    def _convert_decimal_fields(row_dict: dict) -> dict:
        """Convert Decimal values to strings for UserMovement fields."""
        decimal_fields = ['amount', 'shares_change', 'share_price', 'total_amount']
        converted = dict(row_dict)
        for field in decimal_fields:
            if field in converted and isinstance(converted[field], Decimal):
                converted[field] = str(converted[field])
        return converted

    @staticmethod
    def get_user_movements(user_id: int) -> List[UserMovement]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT 
                        cm.id,
                        'cash' as type,
                        cm.account_id,
                        cm.effective_date,
                        cm.created_at,
                        cm.type as cash_type,
                        cm.amount,
                        cm.currency,
                        NULL::bigint as fund_id,
                        NULL::text as fund_name,
                        NULL::numeric as shares_change,
                        NULL::numeric as share_price,
                        NULL::numeric as total_amount,
                        NULL::text as share_movement_type
                      FROM cash_movements cm
                      JOIN accounts a ON cm.account_id = a.id
                      WHERE a.user_id = %s
                      
                      UNION ALL
                      
                      SELECT 
                        fsm.id,
                        'fund_share' as type,
                        fsm.account_id,
                        fsm.effective_date,
                        fsm.created_at,
                        NULL::cash_movement_type as cash_type,
                        NULL::numeric as amount,
                        NULL::text as currency,
                        fsm.fund_id,
                        f.name as fund_name,
                        fsm.shares_change,
                        fsm.share_price,
                        fsm.total_amount,
                        fsm.type::text as share_movement_type
                      FROM fund_share_movements fsm
                      JOIN accounts a ON fsm.account_id = a.id
                      JOIN funds f ON fsm.fund_id = f.id
                      WHERE a.user_id = %s
                      
                      ORDER BY effective_date DESC, created_at DESC""",
                    (user_id, user_id)
                )
                rows = cur.fetchall()
                return [UserMovement(**MovementRepository._convert_decimal_fields(dict(row))) for row in rows]

    @staticmethod
    def get_cash_and_fund_report() -> List[MovementReportRow]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        au.id AS user_id,
                        au.full_name AS user_full_name,
                        a.id AS account_id,
                        a.account_number,
                        cm.id AS cash_movement_id,
                        cm.type AS cash_movement_type,
                        cm.effective_date,
                        cm.amount,
                        fsm.id AS fund_share_movement_id,
                        fsm.shares_change,
                        fsm.share_price
                    FROM app_users au
                    JOIN accounts a ON au.id = a.user_id
                    JOIN cash_movements cm ON a.id = cm.account_id
                    LEFT JOIN fund_share_movements fsm 
                        ON a.id = fsm.account_id 
                        AND cm.id = fsm.cash_movement_id
                    ORDER BY cm.effective_date ASC, cm.id ASC
                    """
                )
                rows = cur.fetchall()
                return [MovementReportRow(**dict(row)) for row in rows]

    @staticmethod
    def get_account_movements(account_id: int) -> List[UserMovement]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT 
                        cm.id,
                        'cash' as type,
                        cm.account_id,
                        cm.effective_date,
                        cm.created_at,
                        cm.type as cash_type,
                        cm.amount,
                        cm.currency,
                        NULL::bigint as fund_id,
                        NULL::text as fund_name,
                        NULL::numeric as shares_change,
                        NULL::numeric as share_price,
                        NULL::numeric as total_amount,
                        NULL::text as share_movement_type
                      FROM cash_movements cm
                      WHERE cm.account_id = %s
                      
                      UNION ALL
                      
                      SELECT 
                        fsm.id,
                        'fund_share' as type,
                        fsm.account_id,
                        fsm.effective_date,
                        fsm.created_at,
                        NULL::cash_movement_type as cash_type,
                        NULL::numeric as amount,
                        NULL::text as currency,
                        fsm.fund_id,
                        f.name as fund_name,
                        fsm.shares_change,
                        fsm.share_price,
                        fsm.total_amount,
                        fsm.type::text as share_movement_type
                      FROM fund_share_movements fsm
                      JOIN funds f ON fsm.fund_id = f.id
                      WHERE fsm.account_id = %s
                      
                      ORDER BY effective_date DESC, created_at DESC""",
                    (account_id, account_id)
                )
                rows = cur.fetchall()
                return [UserMovement(**MovementRepository._convert_decimal_fields(dict(row))) for row in rows]


class FundRepository:
    @staticmethod
    def get_latest_navs_map() -> Dict[int, Dict]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (fund_id)
                        fund_id,
                        nav_per_share,
                        total_aum,
                        as_of_date
                    FROM fund_navs
                    ORDER BY fund_id, as_of_date DESC
                    """
                )
                rows = cur.fetchall()
        return {row["fund_id"]: row for row in rows}

    @staticmethod
    def get_fund_performance(limit: Optional[int] = None) -> List[FundPerformance]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        f.id AS fund_id,
                        f.name AS fund_name,
                        f.currency,
                        fn.as_of_date,
                        fn.nav_per_share,
                        fn.total_aum
                    FROM funds f
                    JOIN fund_navs fn ON fn.fund_id = f.id
                    ORDER BY f.id, fn.as_of_date DESC
                    """
                )
                rows = cur.fetchall()

        funds_map: Dict[int, Dict] = {}
        for row in rows:
            perf = funds_map.setdefault(
                row["fund_id"],
                {
                    "fund_id": row["fund_id"],
                    "fund_name": row["fund_name"],
                    "currency": row["currency"],
                    "latest_nav_per_share": row["nav_per_share"],
                    "navs": [],
                },
            )
            if limit is None or len(perf["navs"]) < limit:
                perf["navs"].append(
                    FundNavPoint(
                        as_of_date=row["as_of_date"],
                        nav_per_share=row["nav_per_share"],
                        total_aum=row["total_aum"],
                    )
                )

        # Ensure nav points are ordered chronologically
        performances: List[FundPerformance] = []
        for perf in funds_map.values():
            perf["navs"].sort(key=lambda n: n.as_of_date)
            performances.append(FundPerformance(**perf))

        return performances

