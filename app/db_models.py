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
    CashMovementUpdate,
    FundShareMovement,
    FundShareMovementCreate,
    FundShareMovementUpdate,
    UserMovement,
    AccountSummary,
    FundPosition,
    Fund,
    FundPerformance,
    FundNav,
    FundNavPoint,
    FundNavCreate,
    FundNavUpdate,
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
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'accounts'
                      AND column_name = 'commission_rate'
                    """
                )
                has_commission_rate = cur.fetchone() is not None
                commission_rate_select = "a.commission_rate" if has_commission_rate else "NULL::numeric AS commission_rate"
                commission_rate_group_by = ", a.commission_rate" if has_commission_rate else ""
                cur.execute(
                    f"""
                    SELECT 
                        a.id AS account_id,
                        a.account_number,
                        {commission_rate_select},
                        u.full_name,
                        u.email,
                        COALESCE(SUM(CASE WHEN cm.type = 'deposit' THEN cm.amount ELSE 0 END), 0) AS total_deposits,
                        COALESCE(SUM(CASE WHEN cm.type = 'withdrawal' THEN cm.amount ELSE 0 END), 0) AS total_withdrawals,
                        COALESCE(SUM(CASE WHEN cm.type = 'fee' THEN cm.amount ELSE 0 END), 0) AS total_fees
                    FROM accounts a
                    JOIN app_users u ON a.user_id = u.id
                    LEFT JOIN cash_movements cm ON cm.account_id = a.id
                    {where_clause}
                    GROUP BY a.id, a.account_number{commission_rate_group_by}, u.full_name, u.email
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

                # Latest share value per fund
                cur.execute(
                    """
                    SELECT DISTINCT ON (fund_id)
                        fund_id,
                        share_value,
                        fund_accumulated,
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
                    explicit_fees = row["total_fees"] or Decimal("0")
                    
                    positions: List[FundPosition] = []
                    account_positions = positions_map.get(row["account_id"], [])
                    total_market_value = Decimal("0")
                    
                    for pos in account_positions:
                        total_shares = pos["total_shares"] or Decimal("0")
                        latest_nav = nav_map.get(pos["fund_id"])
                        latest_nav_value = latest_nav["share_value"] if latest_nav else None
                        market_value = None
                        if latest_nav_value is not None:
                            market_value = Decimal(total_shares) * Decimal(latest_nav_value)
                            total_market_value += market_value

                        positions.append(
                            FundPosition(
                                fund_id=pos["fund_id"],
                                fund_name=pos["fund_name"],
                                currency=pos["currency"],
                                total_shares=total_shares,
                                latest_share_value=latest_nav_value,
                                market_value=market_value,
                            )
                        )

                    # Get commission_rate directly from row (it's in the SELECT)
                    # Access directly since it's guaranteed to be in SELECT
                    commission_rate_raw = row["commission_rate"] if "commission_rate" in row else None
                    
                    # Convert to Decimal for calculation
                    commission_rate = Decimal("0")
                    if commission_rate_raw is not None:
                        if isinstance(commission_rate_raw, Decimal):
                            commission_rate = commission_rate_raw
                        elif isinstance(commission_rate_raw, (int, float)):
                            commission_rate = Decimal(str(commission_rate_raw))
                        else:
                            commission_rate = Decimal(str(commission_rate_raw))
                    
                    # Calculate commissions based on gains (market_value - net_invested)
                    # Net invested before commissions = deposits - withdrawals - explicit fees
                    net_invested_before_commissions = total_deposits - total_withdrawals - explicit_fees
                    total_gains = total_market_value - net_invested_before_commissions
                    
                    # Commission is calculated on gains (only if positive)
                    calculated_commissions = Decimal("0")
                    if total_gains > 0:
                        calculated_commissions = total_gains * commission_rate
                    
                    # Total fees = explicit fees + calculated commissions
                    total_fees = explicit_fees + calculated_commissions
                    
                    # Net invested = deposits - withdrawals - fees (original calculation)
                    # This is the base investment amount, used by the regular dashboard
                    net_invested = total_deposits - total_withdrawals - total_fees
                    
                    # Convert commission_rate to string for response
                    commission_rate_value = str(commission_rate) if commission_rate else None
                    
                    # Force include in model by always setting it (even if None)
                    account_data = {
                        "account_id": row["account_id"],
                        "account_number": row["account_number"],
                        "commission_rate": commission_rate_value,  # Explicitly set, even if None
                        "total_deposits": total_deposits,
                        "total_withdrawals": total_withdrawals,
                        "total_fees": total_fees,
                        "net_invested": net_invested,
                        "positions": positions,
                        "user_full_name": row["full_name"],
                        "user_email": row["email"],
                    }
                    
                    summaries.append(AccountSummary(**account_data))


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
    def get_all_cash_movements() -> List[CashMovement]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        cm.*,
                        u.full_name AS user_name,
                        fsm.fund_id AS fund_id
                    FROM cash_movements cm
                    JOIN accounts a ON cm.account_id = a.id
                    JOIN app_users u ON a.user_id = u.id
                    LEFT JOIN LATERAL (
                        SELECT fund_id
                        FROM fund_share_movements
                        WHERE cash_movement_id = cm.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) fsm ON TRUE
                    ORDER BY cm.effective_date DESC, cm.created_at DESC
                    """
                )
                rows = cur.fetchall()
                return [CashMovement(**dict(row)) for row in rows]

    @staticmethod
    def find_cash_movement_by_id(movement_id: int) -> Optional[CashMovement]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        cm.*,
                        u.full_name AS user_name,
                        fsm.fund_id AS fund_id
                    FROM cash_movements cm
                    JOIN accounts a ON cm.account_id = a.id
                    JOIN app_users u ON a.user_id = u.id
                    LEFT JOIN LATERAL (
                        SELECT fund_id
                        FROM fund_share_movements
                        WHERE cash_movement_id = cm.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) fsm ON TRUE
                    WHERE cm.id = %s
                    """,
                    (movement_id,)
                )
                row = cur.fetchone()
                return CashMovement(**dict(row)) if row else None

    @staticmethod
    def update_cash_movement(movement_id: int, movement_data: CashMovementUpdate) -> Optional[CashMovement]:
        updates = []
        values = []

        if movement_data.type is not None:
            updates.append("type = %s")
            values.append(movement_data.type)
        if movement_data.amount is not None:
            updates.append("amount = %s")
            values.append(movement_data.amount)
        if movement_data.currency is not None:
            updates.append("currency = %s")
            values.append(movement_data.currency)
        if movement_data.effective_date is not None:
            updates.append("effective_date = %s")
            values.append(movement_data.effective_date)

        if not updates:
            return MovementRepository.find_cash_movement_by_id(movement_id)

        values.append(movement_id)
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE cash_movements SET {', '.join(updates)} WHERE id = %s",
                    values
                )
                if cur.rowcount == 0:
                    return None

        return MovementRepository.find_cash_movement_by_id(movement_id)

    @staticmethod
    def delete_cash_movement(movement_id: int) -> bool:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM cash_movements WHERE id = %s", (movement_id,))
                return cur.rowcount > 0

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
    def find_fund_share_movement_by_id(movement_id: int) -> Optional[FundShareMovement]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM fund_share_movements WHERE id = %s",
                    (movement_id,)
                )
                row = cur.fetchone()
                return FundShareMovement(**dict(row)) if row else None

    @staticmethod
    def update_fund_share_movement(
        movement_id: int,
        movement_data: FundShareMovementUpdate
    ) -> Optional[FundShareMovement]:
        updates = []
        values = []

        if movement_data.fund_id is not None:
            updates.append("fund_id = %s")
            values.append(movement_data.fund_id)
        if movement_data.shares_change is not None:
            updates.append("shares_change = %s")
            values.append(movement_data.shares_change)
        if movement_data.share_price is not None:
            updates.append("share_price = %s")
            values.append(movement_data.share_price)
        if movement_data.total_amount is not None:
            updates.append("total_amount = %s")
            values.append(movement_data.total_amount)
        if movement_data.effective_date is not None:
            updates.append("effective_date = %s")
            values.append(movement_data.effective_date)

        if not updates:
            return MovementRepository.find_fund_share_movement_by_id(movement_id)

        values.append(movement_id)
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE fund_share_movements SET {', '.join(updates)} WHERE id = %s",
                    values
                )
                if cur.rowcount == 0:
                    return None

        return MovementRepository.find_fund_share_movement_by_id(movement_id)

    @staticmethod
    def delete_fund_share_movement(movement_id: int) -> bool:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM fund_share_movements WHERE id = %s", (movement_id,))
                return cur.rowcount > 0

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
    def find_all() -> List[Fund]:
        """Get all available funds"""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, name, currency, created_at FROM funds ORDER BY name"
                )
                rows = cur.fetchall()
                return [Fund(**dict(row)) for row in rows]

    @staticmethod
    def find_by_id(fund_id: int) -> Optional[Fund]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, name, currency, created_at FROM funds WHERE id = %s",
                    (fund_id,),
                )
                row = cur.fetchone()
                return Fund(**dict(row)) if row else None

    @staticmethod
    def get_latest_navs_map() -> Dict[int, Dict]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (fund_id)
                        fund_id,
                        share_value,
                        fund_accumulated,
                        as_of_date
                    FROM fund_navs
                    ORDER BY fund_id, as_of_date DESC
                    """
                )
                rows = cur.fetchall()
        return {row["fund_id"]: row for row in rows}

    @staticmethod
    def get_fund_performance_by_id(fund_id: int, limit: Optional[int] = None) -> Optional[FundPerformance]:
        """Get performance data for a specific fund"""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if fund exists
                cur.execute("SELECT id, name, currency FROM funds WHERE id = %s", (fund_id,))
                fund_row = cur.fetchone()
                if not fund_row:
                    return None

                cur.execute(
                    """
                    SELECT 
                        fn.as_of_date,
                        fn.fund_accumulated,
                        fn.shares_amount,
                        fn.share_value,
                        fn.delta_previous,
                        fn.delta_since_origin
                    FROM fund_navs fn
                    WHERE fn.fund_id = %s
                    ORDER BY fn.as_of_date DESC
                    LIMIT %s
                    """,
                    (fund_id, limit if limit else 365)
                )
                rows = cur.fetchall()

                navs = [
                    FundNavPoint(
                        as_of_date=row["as_of_date"],
                        fund_accumulated=row["fund_accumulated"],
                        shares_amount=row["shares_amount"],
                        share_value=row["share_value"],
                        delta_previous=row.get("delta_previous"),
                        delta_since_origin=row.get("delta_since_origin"),
                    )
                    for row in rows
                ]

                # Sort nav points chronologically
                navs.sort(key=lambda n: n.as_of_date)
                latest_nav = navs[-1].share_value if navs else None

                return FundPerformance(
                    fund_id=fund_id,
                    fund_name=fund_row["name"],
                    currency=fund_row["currency"],
                    latest_share_value=latest_nav,
                    navs=navs,
                )

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
                        fn.fund_accumulated,
                        fn.shares_amount,
                        fn.share_value,
                        fn.delta_previous,
                        fn.delta_since_origin
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
                    "latest_share_value": row["share_value"],
                    "navs": [],
                },
            )
            if limit is None or len(perf["navs"]) < limit:
                perf["navs"].append(
                    FundNavPoint(
                        as_of_date=row["as_of_date"],
                        fund_accumulated=row["fund_accumulated"],
                        shares_amount=row["shares_amount"],
                        share_value=row["share_value"],
                        delta_previous=row.get("delta_previous"),
                        delta_since_origin=row.get("delta_since_origin"),
                    )
                )

        # Ensure nav points are ordered chronologically
        performances: List[FundPerformance] = []
        for perf in funds_map.values():
            perf["navs"].sort(key=lambda n: n.as_of_date)
            performances.append(FundPerformance(**perf))

        return performances

    @staticmethod
    def get_all_navs(fund_id: Optional[int] = None) -> List[FundNav]:
        where_clause = ""
        params: List = []
        if fund_id is not None:
            where_clause = "WHERE fund_id = %s"
            params.append(fund_id)

        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT *
                    FROM fund_navs
                    {where_clause}
                    ORDER BY as_of_date DESC, created_at DESC
                    """,
                    params,
                )
                rows = cur.fetchall()
                return [FundNav(**dict(row)) for row in rows]

    @staticmethod
    def create_nav(nav_data: FundNavCreate) -> FundNav:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO fund_navs
                    (fund_id, as_of_date, fund_accumulated, shares_amount, share_value, delta_previous, delta_since_origin)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        nav_data.fund_id,
                        nav_data.as_of_date,
                        nav_data.fund_accumulated,
                        nav_data.shares_amount,
                        nav_data.share_value,
                        nav_data.delta_previous,
                        nav_data.delta_since_origin,
                    ),
                )
                row = cur.fetchone()
                return FundNav(**dict(row))

    @staticmethod
    def update_nav(nav_id: int, nav_data: FundNavUpdate) -> Optional[FundNav]:
        updates = []
        values = []

        if nav_data.as_of_date is not None:
            updates.append("as_of_date = %s")
            values.append(nav_data.as_of_date)
        if nav_data.fund_accumulated is not None:
            updates.append("fund_accumulated = %s")
            values.append(nav_data.fund_accumulated)
        if nav_data.shares_amount is not None:
            updates.append("shares_amount = %s")
            values.append(nav_data.shares_amount)
        if nav_data.share_value is not None:
            updates.append("share_value = %s")
            values.append(nav_data.share_value)
        if nav_data.delta_previous is not None:
            updates.append("delta_previous = %s")
            values.append(nav_data.delta_previous)
        if nav_data.delta_since_origin is not None:
            updates.append("delta_since_origin = %s")
            values.append(nav_data.delta_since_origin)

        if not updates:
            with get_db() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM fund_navs WHERE id = %s", (nav_id,))
                    row = cur.fetchone()
                    return FundNav(**dict(row)) if row else None

        values.append(nav_id)
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"UPDATE fund_navs SET {', '.join(updates)} WHERE id = %s RETURNING *",
                    values,
                )
                row = cur.fetchone()
                return FundNav(**dict(row)) if row else None

    @staticmethod
    def delete_nav(nav_id: int) -> bool:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM fund_navs WHERE id = %s", (nav_id,))
                return cur.rowcount > 0

