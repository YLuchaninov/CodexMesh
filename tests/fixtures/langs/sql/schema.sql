
CREATE TABLE t_orders (id INT, user_id INT, amount INT);
CREATE TABLE t_users (id INT, name TEXT);

CREATE VIEW v_big_orders AS
SELECT o.id, u.name, o.amount
FROM t_orders o
JOIN t_users u ON u.id = o.user_id
WHERE o.amount > 100;
