"""Exact-cents, event-date analytics. Never infer missing coverage as zero."""
from collections import Counter, defaultdict
from datetime import date


def total(rows, field):
    values = [r[field] for r in rows]
    return None if any(v is None for v in values) else sum(values)


def ratio(a, b):
    return round(100 * a / b, 2) if a is not None and b not in (None, 0) else None


def subtract(a, b):
    return None if a is None or b is None else a - b


def analyze(data):
    from .validation import validate, ContractError
    from .decisions import build_decisions, experiments, market_sources
    quality = validate(data)
    t, meta = data['tables'], data['metadata']
    unsafe=[q for q in quality if q["status"]=="FAIL" and (q["id"].startswith("fk_") or q["id"]=="delivery_dates")]
    if unsafe: raise ContractError("Report withheld: invalid relationships or delivery dates")
    cover = meta.get('coverage', {})
    known = lambda *names: all(cover.get(n, False) for n in names)
    orders = {r['id']: r for r in t['orders']}
    items = {r['id']: r for r in t['order_items']}
    products = {r['id']: r for r in t['products']}
    suppliers = {r['id']: r for r in t['suppliers']}
    delivered = [r for r in t['order_items'] if orders[r['order_id']]['status'] == 'delivered']
    gross = sum(r['quantity'] * r['unit_price_cents'] for r in delivered) if known('orders', 'order_items') else None
    discounts = total(delivered, 'discount_cents') if known('orders', 'order_items') else None
    credits = total(t['credit_notes'], 'amount_cents') if known('credit_notes') else None
    net = subtract(subtract(gross, discounts), credits)
    restocks = [r for r in t['returns'] if r['restock']]
    cost_known = known('orders', 'order_items', 'returns') and all(r['unit_cost_cents'] is not None for r in delivered) and all(items[r['order_item_id']]['unit_cost_cents'] is not None for r in restocks)
    cogs = sum(r['quantity'] * r['unit_cost_cents'] for r in delivered) - sum(r['quantity'] * items[r['order_item_id']]['unit_cost_cents'] for r in restocks) if cost_known else None
    opex = total(t['expenses'], 'amount_cents') if known('expenses') else None
    variable = total([r for r in t['expenses'] if r['variable']], 'amount_cents') if known('expenses') else None
    settled = [p for p in t['payments'] if p['status'] == 'settled']
    refunded = [p for p in t['refunds'] if p['status'] == 'settled']
    cash_in = total(settled, 'amount_cents') if known('payments') else None
    cash_out = (sum(r['amount_cents'] for r in refunded) + sum(r['paid_cents'] for r in t['expenses']) + sum(r['paid_cents'] for r in t['purchase_orders'])) if known('refunds', 'expenses', 'purchase_orders') else None
    profit = subtract(net, cogs)
    inventory = []
    asof = date.fromisoformat(meta['as_of'])
    for v in t['variants']:
        moves = [r for r in t['movements'] if r['variant_id'] == v['id']]
        line_ids = {r['id'] for r in t['order_items'] if r['variant_id'] == v['id']}
        onhand = total(moves, 'quantity') if known('movements','variants') else None
        reserved = sum(r['quantity'] for r in t['reservations'] if r['order_item_id'] in line_ids and r['status'] == 'active') if known('reservations','order_items','orders','variants') else None
        transit = sum(r['ordered_qty'] - r['received_qty'] for r in t['purchase_orders'] if r['variant_id'] == v['id'] and r['status'] != 'cancelled') if known('purchase_orders','variants') else None
        sold = -sum(r['quantity'] for r in moves if r['kind'] == 'sale') if known('movements','variants') else None
        restocked=sum(r['quantity'] for r in moves if r['kind']=='return') if known('movements','variants') else None
        net_sold=subtract(sold,restocked)
        inflow = sum(r['quantity'] for r in moves if r['kind'] in ('opening', 'receipt')) if known('movements','variants') else None
        last = max((r['date'] for r in moves if r['kind'] == 'sale'), default=None)
        age = (asof - date.fromisoformat(last)).days if last else None
        if not known('movements','variants'): age=None
        cost=v['cost_cents'] if known('variants') else None
        available = subtract(onhand, reserved)
        status = 'UNKNOWN' if available is None or cost is None else 'REVIEW' if available < 0 else 'STOCKOUT' if available == 0 else 'REORDER' if available < 10 else 'SLOW' if age is None or age >= 30 else 'HEALTHY'
        lifecycle=products[v['product_id']]['lifecycle'] if known('products') else None
        if lifecycle in ('idea','sample'): status='PRELAUNCH'
        if lifecycle is None: status='UNKNOWN'
        inventory.append(dict(lifecycle=lifecycle,sku=v['id'], name=products[v['product_id']]['name'], category=products[v['product_id']]['category'], size=v['size'], color=v['color'], on_hand=onhand, reserved=reserved, available=available, in_transit=transit, cost_cents=cost, value_cents=onhand*cost if onhand is not None and cost is not None else None, sold_units=sold, sell_through_pct=ratio(net_sold,inflow), days_since_sale=age, status=status))
    customer_counts = Counter(r['customer_id'] for r in t['orders'] if r['status']=='delivered')
    kpis = dict(gross_revenue_cents=gross, discounts_cents=discounts, credits_cents=credits, net_revenue_cents=net, cogs_cents=cogs, gross_profit_cents=profit, gross_margin_pct=ratio(profit,net), opex_cents=opex, variable_expenses_cents=variable, contribution_cents=subtract(profit,variable), operating_proxy_cents=subtract(profit,opex), cash_in_cents=cash_in, cash_out_cents=cash_out, net_cash_cents=subtract(cash_in,cash_out), orders=len(orders) if known('orders') else None, delivered_orders=sum(r['status']=='delivered' for r in orders.values()) if known('orders') else None, repeat_rate_pct=ratio(sum(n>1 for n in customer_counts.values()),len(customer_counts)) if known('orders') else None, inventory_value_cents=total(inventory,'value_cents') if known('variants','movements') else None)
    trend = defaultdict(lambda:dict(net_revenue_cents=0,cogs_cents=0,opex_cents=0,net_cash_cents=0))
    for r in delivered:
        m = trend[orders[r['order_id']]['delivered_date'][:7]]
        m['net_revenue_cents'] += r['quantity']*r['unit_price_cents']-r['discount_cents']
        m['cogs_cents'] += r['quantity']*(r['unit_cost_cents'] or 0)
    for r in t['credit_notes']: trend[r['date'][:7]]['net_revenue_cents'] -= r['amount_cents']
    for r in restocks: trend[r['date'][:7]]['cogs_cents'] -= r['quantity']*(items[r['order_item_id']]['unit_cost_cents'] or 0)
    for r in t['expenses']:
        trend[r['date'][:7]]['opex_cents'] += r['amount_cents']
        trend[r['date'][:7]]['net_cash_cents'] -= r['paid_cents']
    for r in settled: trend[r['date'][:7]]['net_cash_cents'] += r['amount_cents']
    for r in refunded: trend[r['date'][:7]]['net_cash_cents'] -= r['amount_cents']
    for r in t['purchase_orders']: trend[r['date'][:7]]['net_cash_cents'] -= r['paid_cents']
    trends=[]
    for month, values in sorted(trend.items()):
        if net is None: values['net_revenue_cents']=None
        if not cost_known: values['cogs_cents']=None
        if opex is None: values['opex_cents']=None
        if cash_in is None or cash_out is None: values['net_cash_cents']=None
        trends.append(dict(month=month,**values))
    order_view=[]
    for o in orders.values():
        lines=[r for r in t['order_items'] if r['order_id']==o['id']]
        line_ids={r['id'] for r in lines}
        ordered=sum(r['quantity']*r['unit_price_cents']-r['discount_cents'] for r in lines)
        recognized=(ordered if o['status']=='delivered' else 0)-sum(r['amount_cents'] for r in t['credit_notes'] if r['order_item_id'] in line_ids)
        order_view.append(dict(id=o['id'],date=o['date'],channel=o['channel'],status=o['status'],customer_id=o['customer_id'],ordered_cents=ordered if known('orders','order_items') else None,recognized_cents=recognized if known('orders','order_items','credit_notes') else None,settled_cents=sum(r['amount_cents'] for r in settled if r['order_id']==o['id']) if known('payments') else None,refunded_cents=sum(r['amount_cents'] for r in refunded if r['order_id']==o['id']) if known('refunds') else None))
    channels=[]
    for ch in sorted({r['channel'] for r in orders.values()}|{r['channel'] for r in t['funnel']}):
        fs=[r for r in t['funnel'] if r['channel']==ch]
        os=[r for r in order_view if r['channel']==ch]
        visits=total(fs,'visits') if fs and known('funnel') else None
        leads=total(fs,'leads') if fs and known('funnel') else None
        channels.append(dict(channel=ch,visits=visits,leads=leads,orders=len(os) if known('orders') else None,delivered_orders=sum(r['status']=='delivered' for r in os) if known('orders') else None,net_revenue_cents=total(os,'recognized_cents') if known('orders','order_items','credit_notes') else None,spend_cents=total(fs,'spend_cents') if fs and known('funnel') else None,conversion_pct=ratio(sum(r['status']!='cancelled' for r in os),visits) if known('orders') else None))
    cohorts=[]
    # First delivered order, fixed 30-day repeat window and per-customer maturity.
    firsts={c:min(r['delivered_date'] for r in orders.values() if r['customer_id']==c and r['status']=='delivered') for c in customer_counts}
    for month in sorted({d[:7] for d in firsts.values()}):
        cs=[c for c,d in firsts.items() if d[:7]==month]
        mature=[c for c in cs if (asof-date.fromisoformat(firsts[c])).days>=30]
        repeat=sum(sum(r['customer_id']==c and r['status']=='delivered' and 0 <= (date.fromisoformat(r['delivered_date'])-date.fromisoformat(firsts[c])).days <=30 for r in orders.values())>1 for c in mature)
        cohorts.append(dict(month=month,customers=len(cs),repeat_customers=repeat if mature else None,repeat_rate_pct=ratio(repeat,len(mature)) if known('orders') else None,mature_30d=len(mature)))
    purchases=[dict(id=r['id'],supplier=suppliers[r['supplier_id']]['name'],sku=r['variant_id'],ordered_qty=r['ordered_qty'],received_qty=r['received_qty'],in_transit=r['ordered_qty']-r['received_qty'] if r['status']!='cancelled' else 0,status=r['status'],ordered_cents=r['ordered_qty']*r['unit_cost_cents'],paid_cents=r['paid_cents']) for r in t['purchase_orders']]
    report=dict(meta=dict(coverage=dict(cover),synthetic=True,as_of=meta['as_of'],seed=meta['seed'],scenario=meta['scenario'],currency='MXN',status='PASS' if all(q['status']=='PASS' for q in quality) else 'BLOCKED',policy='Provisional'), kpis=kpis,trend=trends,inventory=inventory,channels=channels,cohorts=cohorts,products=t['products'],orders=order_view,purchases=purchases,quality=quality,market=market_sources(),experiments=experiments(),decisions=[])
    if not known('orders'): report['cohorts']=[]
    if not known('products'): report['products']=[]
    if not known('purchase_orders'): report['purchases']=[]
    report['unmet_demand']=t['unmet_demand'] if known('unmet_demand') else None
    report['decisions']=build_decisions(report)
    return report
