"""Input contracts and business invariants, with evidence for every check."""
from collections import Counter, defaultdict
from datetime import date

SCHEMA = {
 'products':'id name category collection lifecycle',
 'variants':'id product_id size color price_cents cost_cents',
 'suppliers':'id name',
 'purchase_orders':'id supplier_id variant_id ordered_qty received_qty unit_cost_cents status date paid_cents',
 'customers':'id acquired_date',
 'orders':'id customer_id channel campaign_id date delivered_date status',
 'order_items':'id order_id variant_id quantity unit_price_cents discount_cents unit_cost_cents',
 'payments':'id order_id date amount_cents status',
 'refunds':'id order_id date amount_cents status',
 'credit_notes':'id order_item_id date amount_cents reason',
 'returns':'id order_item_id date quantity restock',
 'movements':'id variant_id date kind quantity reference_id',
 'reservations':'id order_item_id quantity status',
 'expenses':'id date category amount_cents paid_cents variable',
 'funnel':'id date channel campaign_id visits leads spend_cents',
 'unmet_demand':'id date variant_id quantity reason',
}
NULLABLE = {('variants','cost_cents'),('order_items','unit_cost_cents'),('orders','delivered_date'),('funnel','visits'),('funnel','leads')}
INTEGER = {'quantity','ordered_qty','received_qty','restock','variable','visits','leads'}
ENUMS = {
 ('orders','status'):{'delivered','shipped','paid','pending','cancelled'},
 ('payments','status'):{'settled','pending','failed'},
 ('refunds','status'):{'settled','pending'},
 ('reservations','status'):{'active','released'},
 ('movements','kind'):{'opening','receipt','sale','return','adjustment','supplier_return'},
}

class ContractError(ValueError):
    pass


def check_structure(data):
    if not isinstance(data,dict) or set(data)!={'metadata','tables'}:
        raise ContractError('Expected metadata and tables only')
    meta=data['metadata']
    if not isinstance(meta,dict) or meta.get('synthetic') is not True:
        raise ContractError('Only explicitly synthetic data is authorized')
    if meta.get('currency')!='MXN' or type(meta.get('seed')) is not int or not isinstance(meta.get('scenario'),str):
        raise ContractError('Metadata requires MXN, integer seed and scenario')
    try: date.fromisoformat(meta['as_of'])
    except (KeyError,TypeError,ValueError): raise ContractError('Invalid as_of')
    if not isinstance(data['tables'],dict) or set(data['tables'])!=set(SCHEMA): raise ContractError('Missing or unexpected tables')
    if not isinstance(meta.get('coverage'),dict) or set(meta['coverage'])!=set(SCHEMA) or any(type(v) is not bool for v in meta['coverage'].values()):
        raise ContractError('Explicit boolean coverage required for each table')
    for table, cols in SCHEMA.items():
        rows=data['tables'][table]
        if not isinstance(rows,list): raise ContractError(f'{table}: expected rows')
        for row in rows:
            if not isinstance(row,dict) or set(row)!=set(cols.split()): raise ContractError(f'{table}: unexpected columns')
            for key,v in row.items():
                if v is None and (table,key) in NULLABLE: continue
                numeric=key.endswith('_cents') or key in INTEGER
                if numeric:
                    if type(v) is not int or abs(v)>9223372036854775807: raise ContractError(f'{table}.{key}: integer required')
                    if v<0 and not(table=='movements' and key=='quantity'): raise ContractError(f'{table}.{key}: negative value')
                    if key in ('variable','restock') and v not in (0,1): raise ContractError('Invalid flag')
                elif not isinstance(v,str) or not v or len(v)>500:
                    raise ContractError(f'{table}.{key}: nonempty string <=500 required')
                if key in ('date','delivered_date','acquired_date'):
                    try: parsed=date.fromisoformat(v)
                    except (TypeError,ValueError): raise ContractError(f'{table}.{key}: invalid date')
                    if v>meta['as_of']: raise ContractError(f'{table}.{key}: after snapshot')
                if (table,key) in ENUMS and v not in ENUMS[table,key]: raise ContractError(f'{table}.{key}: invalid enum')
    return data


def validate(data):
    check_structure(data)
    t=data['tables']; results=[]
    def add(cid,ok,message,refs,status=None):
        results.append(dict(id=cid,status=status or ('PASS' if ok else 'FAIL'),message=message,evidence_refs=refs))
    ids={name:{r['id'] for r in rows} for name,rows in t.items()}
    for table, rows in t.items():
        add('unique_'+table,len(ids[table])==len(rows),'IDs únicos: '+table,['tables/'+table])
        add('coverage_'+table,data['metadata']['coverage'][table],'Cobertura declarada: '+table,['metadata/coverage/'+table],status='PASS' if data['metadata']['coverage'][table] else 'UNKNOWN')
    refs={'product_id':'products','supplier_id':'suppliers','variant_id':'variants','customer_id':'customers','order_id':'orders','order_item_id':'order_items'}
    relationships=True
    for table,rows in t.items():
        for key,target in refs.items():
            if key not in SCHEMA[table].split():continue
            bad=[r['id'] for r in rows if r[key] not in ids[target]]
            relationships &= not bad
            add('fk_'+table+'_'+key,not bad,'Referencias válidas: '+table+'.'+key,['tables/'+table,'tables/'+target])
    if not relationships: return results
    orders={r['id']:r for r in t['orders']}; items={r['id']:r for r in t['order_items']}
    variants={r['id']:r for r in t['variants']}
    pos={r['id']:r for r in t['purchase_orders']}
    returns={r['id']:r for r in t['returns']}
    costs=all(r['cost_cents'] is not None for r in t['variants']) and all(r['unit_cost_cents'] is not None for r in t['order_items'])
    add('cost_coverage',costs,'Costos estándar completos; faltantes retienen márgenes y valoración',['tables/variants','tables/order_items'],status='PASS' if costs else 'UNKNOWN')
    bad=[]
    for r in t['order_items']:
        if r['quantity']<=0 or r['discount_cents']>r['quantity']*r['unit_price_cents']: bad.append(r['id'])
    add('line_amounts',not bad,'Cantidad positiva y descuento no mayor al bruto',['tables/order_items'])
    add('delivery_dates',all((o['status']=='delivered')==(o['delivered_date'] is not None) and (o['delivered_date'] is None or o['delivered_date']>=o['date']) for o in orders.values()),'Entrega y reconocimiento tienen fecha consistente',['tables/orders'])
    po_ok=all(0<=r['received_qty']<=r['ordered_qty'] and r['paid_cents']<=r['ordered_qty']*r['unit_cost_cents'] for r in pos.values())
    add('po_quantities',po_ok,'Recepción parcial y pago dentro de orden de compra',['tables/purchase_orders'])
    onhand=defaultdict(int); nonnegative=True
    for r in sorted(t['movements'],key=lambda r:(r['date'],0 if r['quantity']>=0 else 1,r['id'])):
        onhand[r['variant_id']]+=r['quantity']
        if onhand[r['variant_id']]<0:nonnegative=False
    add('stock_nonnegative',nonnegative,'Ledger no negativo por SKU en cada fecha',['tables/movements'])
    linkage=True
    for r in t['movements']:
        ref=r['reference_id']; kind=r['kind']
        if kind=='sale': linkage &= ref in items and items[ref]['variant_id']==r['variant_id'] and r['quantity']<0 and orders[items[ref]['order_id']]['status'] in ('shipped','delivered') and r['date']>=orders[items[ref]['order_id']]['date']
        elif kind=='receipt': linkage &= ref in pos and pos[ref]['variant_id']==r['variant_id'] and r['quantity']>0 and r['date']>=pos[ref]['date']
        elif kind=='return': linkage &= ref in returns and returns[ref]['restock']==1 and items[returns[ref]['order_item_id']]['variant_id']==r['variant_id'] and r['quantity']>0 and r['date']==returns[ref]['date']
        elif kind=='opening': linkage &= r['quantity']>=0
        elif kind=='supplier_return': linkage &= ref in pos and pos[ref]['variant_id']==r['variant_id'] and r['quantity']<0
    add('movement_references',bool(linkage),'Movimiento con referencia, signo y estado válidos',['tables/movements'])
    sales_ok=True
    for r in items.values():
        actual=-sum(m['quantity'] for m in t['movements'] if m['kind']=='sale' and m['reference_id']==r['id'])
        expected=r['quantity'] if orders[r['order_id']]['status'] in ('shipped','delivered') else 0
        sales_ok &= actual==expected
    add('sales_ledger',sales_ok,'Salidas concilian con artículos despachados',['tables/movements','tables/order_items'])
    receipts_ok=all(sum(m['quantity'] for m in t['movements'] if m['kind']=='receipt' and m['reference_id']==r['id'])==r['received_qty'] for r in pos.values())
    add('receipt_ledger',receipts_ok,'Entradas concilian con recepciones de compra',['tables/movements','tables/purchase_orders'])
    returns_ok=True
    for r in returns.values():
        line=items[r['order_item_id']]; order=orders[line['order_id']]
        returns_ok &= order['status']=='delivered' and r['date']>=(order['delivered_date'] or order['date'])
        returns_ok &= sum(m['quantity'] for m in t['movements'] if m['kind']=='return' and m['reference_id']==r['id'])==(r['quantity'] if r['restock'] else 0)
    for line in items.values(): returns_ok &= sum(r['quantity'] for r in returns.values() if r['order_item_id']==line['id'])<=line['quantity']
    add('returns_ledger',returns_ok,'Devolución física separada; cantidad y restock conciliados',['tables/returns','tables/movements'])
    reserve_ok=True; reserved=defaultdict(int)
    for line in items.values():
        actual=sum(r['quantity'] for r in t['reservations'] if r['order_item_id']==line['id'] and r['status']=='active')
        expected=line['quantity'] if orders[line['order_id']]['status'] in ('paid','pending') else 0
        reserve_ok &= actual==expected
        reserved[line['variant_id']]+=actual
    reserve_ok &= all(onhand[v]>=q for v,q in reserved.items())
    add('reservations',reserve_ok,'Reservas abiertas concilian y no exceden existencia',['tables/reservations','tables/movements'])
    credit_ok=True
    for line in items.values():
        cs=[r for r in t['credit_notes'] if r['order_item_id']==line['id']]
        order=orders[line['order_id']]
        credit_ok &= sum(r['amount_cents'] for r in cs)<=line['quantity']*line['unit_price_cents']-line['discount_cents']
        credit_ok &= all(order['status']=='delivered' and r['date']>=(order['delivered_date'] or order['date']) for r in cs)
    add('credit_limits',credit_ok,'Notas de crédito no exceden ingreso y siguen entrega',['tables/credit_notes','tables/order_items'])
    cash_ok=True
    for o in orders.values():
        net=sum(r['quantity']*r['unit_price_cents']-r['discount_cents'] for r in items.values() if r['order_id']==o['id'])
        ps=[r for r in t['payments'] if r['order_id']==o['id'] and r['status']=='settled']
        rs=[r for r in t['refunds'] if r['order_id']==o['id'] and r['status']=='settled']
        paid=sum(r['amount_cents'] for r in ps); refunded=sum(r['amount_cents'] for r in rs)
        cash_ok &= 0<=refunded<=paid<=net
        if o['status'] in ('paid','shipped','delivered'):cash_ok &= paid==net
        for r in ps+rs: cash_ok &= r['date']>=o['date']
        for r in rs: cash_ok &= sum(x['amount_cents'] for x in rs if x['date']<=r['date'])<=sum(x['amount_cents'] for x in ps if x['date']<=r['date'])
    add('payment_reconciliation',cash_ok,'Política demo prepago: cobro, pedido y reembolso concilian',['tables/payments','tables/refunds','tables/orders'])
    add('marketing_spend',sum(r['amount_cents'] for r in t['expenses'] if r['category']=='marketing')==sum(r['spend_cents'] for r in t['funnel']),'Gasto de marketing registrado una vez en gastos; funnel es descriptivo',['tables/expenses','tables/funnel'])
    shipment_payment_ok=True
    for move in (r for r in t['movements'] if r['kind']=='sale' and r['reference_id'] in items):
        line=items[move['reference_id']]; order=orders[line['order_id']]
        expected=sum(x['quantity']*x['unit_price_cents']-x['discount_cents'] for x in items.values() if x['order_id']==order['id'])
        paid=sum(x['amount_cents'] for x in t['payments'] if x['order_id']==order['id'] and x['status']=='settled' and x['date']<=move['date'])
        shipment_payment_ok &= paid==expected and (order['delivered_date'] is None or move['date']<=order['delivered_date'])
    add('shipment_prepayment',shipment_payment_ok,'Cobro completo previo al despacho y despacho no posterior a entrega',['tables/movements','tables/payments','tables/orders'])
    add('expense_payments',all(r['paid_cents']<=r['amount_cents'] for r in t['expenses']),'Gastos: efectivo separado del devengo',['tables/expenses'])
    return results
