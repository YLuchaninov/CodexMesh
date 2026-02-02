
CREATE TABLE t_src (id INT, v INT);
CREATE TABLE t_dst (id INT, v INT);

INSERT INTO t_dst
SELECT id, v FROM t_src;

CREATE VIEW v_dst AS
SELECT * FROM t_dst;
