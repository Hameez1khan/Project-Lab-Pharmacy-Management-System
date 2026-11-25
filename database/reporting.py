from contextlib import closing
from database.db import get_connection


def report_data(start, end):
    if start > end:
        raise ValueError("The start date must not follow the end date.")
    with closing(get_connection()) as c:
        c.execute("BEGIN")

        def query(sql, args=()):
            cur = c.execute(sql, args)
            return [col[0] for col in cur.description], [tuple(r) for r in cur]

        flow = """WITH flow(dt, method, sale, refund, receipt) AS (
            SELECT sale_datetime, payment_method, total_amount, 0, 1 FROM sales
            UNION ALL
            SELECT r.return_datetime, s.payment_method, 0, r.total_amount, 0
            FROM returns r LEFT JOIN sales s ON s.id=r.sale_id
        ) """
        period = " WHERE dt >= ? AND dt < date(?,'+1 day') "
        args = (start, end)
        amounts = """sum(receipt) AS Receipts, round(sum(sale),2) AS "Sales (Ft)",
            round(sum(refund),2) AS "Refunds (Ft)", round(sum(sale-refund),2) AS "Net (Ft)" """

        def grouped(group):
            return query(flow + "SELECT " + group + ", " + amounts + " FROM flow"
                         + period + "GROUP BY 1 ORDER BY 1", args)

        result = {
            "Daily": grouped("date(dt) AS Day"),
            "Monthly": grouped("substr(dt,1,7) AS Month"),
            "Payment": grouped("coalesce(nullif(method,''),'Unknown') AS Payment"),
        }
        result["Products"] = query("""WITH moves(dt,product_id,name,sold,returned,value) AS (
            SELECT s.sale_datetime,i.product_id,i.product_name,i.quantity,0,i.subtotal
            FROM sale_items i JOIN sales s ON s.id=i.sale_id
            UNION ALL
            SELECT r.return_datetime,i.product_id,i.product_name,0,i.quantity,-i.subtotal
            FROM return_items i JOIN returns r ON r.id=i.return_id)
            SELECT coalesce(p.name,m.name,'Unknown') AS Product, sum(sold) AS Sold,
            sum(returned) AS Returned, round(sum(value),2) AS "Net (Ft)"
            FROM moves m LEFT JOIN products p ON p.id=m.product_id """ + period +
            "GROUP BY m.product_id,1 ORDER BY Sold DESC, Product", args)
        result["Returns"] = query("""SELECT id AS "Return ID",sale_id AS Receipt,
            return_datetime AS Returned, total_amount AS "Refund (Ft)" FROM returns
            WHERE return_datetime >= ? AND return_datetime < date(?,'+1 day')
            ORDER BY return_datetime DESC,id DESC""", args)
        result["Low stock now"] = query("""WITH stock AS (
            SELECT p.name AS Product, p.min_stock_level AS Minimum,
                   coalesce(sum(b.quantity), 0) AS Available
            FROM products p
            LEFT JOIN batches b ON b.product_id = p.id
                AND date(b.expiry_date) >= date('now','localtime')
            GROUP BY p.id
        )
        SELECT Product, Available, Minimum, Minimum - Available AS "Suggested order (units)"
        FROM stock
        WHERE Available < Minimum
        ORDER BY "Suggested order (units)" DESC, Product""")
        result["Expiry now"] = query("""SELECT p.name AS Product,b.batch_number AS Batch,
            b.expiry_date AS Expiry,b.quantity AS Units,
            CASE WHEN date(b.expiry_date) IS NULL THEN 'Check date'
                 WHEN date(b.expiry_date)<date('now','localtime') THEN 'Expired'
                 ELSE 'Within 30 days' END AS Status,
            round(b.quantity*b.purchase_unit_cost,2) AS "Stock value (Ft)"
            FROM batches b JOIN products p ON p.id=b.product_id WHERE b.quantity>0
            AND (date(b.expiry_date) IS NULL OR date(b.expiry_date)<=date('now','localtime','+30 days'))
            ORDER BY date(b.expiry_date),p.name""")
        return result