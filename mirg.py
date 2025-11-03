# migrate_sqlite_to_postgres.py
import os
from collections import defaultdict, deque
from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:///data.db")
PG_URL     = os.getenv("PG_URL",     "postgresql+psycopg://appuser:StrongPass!@127.0.0.1:5432/appdb")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))

def reflect(engine: Engine) -> MetaData:
    md = MetaData()
    md.reflect(bind=engine)
    return md

def topo_tables(md: MetaData):
    tables = list(md.tables.values())
    name2t = {t.name: t for t in tables}
    indeg = {t.name: 0 for t in tables}
    graph = defaultdict(set)

    for t in tables:
        for fk in t.foreign_keys:
            p = fk.column.table.name
            c = t.name
            if p != c and c not in graph[p]:
                graph[p].add(c)

    for p, kids in graph.items():
        for k in kids:
            indeg[k] += 1

    q = deque([n for n, d in indeg.items() if d == 0])
    order = []
    while q:
        n = q.popleft()
        order.append(name2t[n])
        for k in graph.get(n, []):
            indeg[k] -= 1
            if indeg[k] == 0:
                q.append(k)

    if len(order) != len(tables):
        # На случай циклов FK — добавим оставшиеся в конец
        seen = {t.name for t in order}
        order.extend([name2t[n] for n in name2t if n not in seen])
    return order

def fetch_batches(src_engine: Engine, table: Table, size: int):
    with src_engine.connect() as conn:
        res = conn.execute(select(table))
        while True:
            rows = res.fetchmany(size)
            if not rows:
                break
            yield [dict(r._mapping) for r in rows]

def reset_serial(pg_engine: Engine, table: Table):
    # Сдвигаем sequence по id, если есть
    if "id" not in table.c:
        return
    with pg_engine.begin() as conn:
        try:
            conn.execute(text(f"""
                SELECT setval(pg_get_serial_sequence('{table.name}', 'id'),
                              COALESCE((SELECT MAX(id) FROM "{table.name}"), 0));
            """))
        except SQLAlchemyError:
            pass

def copy_table(src_engine: Engine, dst_engine: Engine, tname: str, pg_meta: MetaData):
    if tname not in pg_meta.tables:
        print(f"[SKIP] {tname}: нет в PG (пропущено сценарием миграций)")
        return 0
    target = pg_meta.tables[tname]
    total = 0
    # Отложим проверки FK для транзакции
    with dst_engine.begin() as conn:
        try:
            conn.execute(text("SET CONSTRAINTS ALL DEFERRED;"))
        except SQLAlchemyError:
            pass
    for batch in fetch_batches(src_engine, target, BATCH_SIZE):
        if not batch:
            continue
        with dst_engine.begin() as conn:
            conn.execute(target.insert(), batch)
        total += len(batch)
    reset_serial(dst_engine, target)
    return total

def main():
    sqlite_engine = create_engine(SQLITE_URL)
    pg_engine = create_engine(PG_URL)

    src_md = reflect(sqlite_engine)
    dst_md = reflect(pg_engine)

    missing = set(src_md.tables) - set(dst_md.tables)
    if missing:
        raise SystemExit(f"В PG нет таблиц (сначала alembic upgrade head): {sorted(missing)}")

    order = topo_tables(src_md)
    print("Порядок копирования:", " -> ".join([t.name for t in order]))

    total = 0
    for t in order:
        n = t.name
        cnt = copy_table(sqlite_engine, pg_engine, n, dst_md)
        print(f"[OK] {n}: {cnt} строк")
        total += cnt

    print(f"Готово. Всего перенесено: {total} строк")

if __name__ == "__main__":
    main()
