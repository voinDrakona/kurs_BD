-- ========== Таблицы ===========
CREATE TABLE contract_types (
    contract_type_id  SERIAL PRIMARY KEY,
    name              TEXT NOT NULL UNIQUE
);

CREATE TABLE execution_stages (
    stage_id    SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE vat_rates (
    vat_id      SERIAL PRIMARY KEY,
    percent     NUMERIC(5,2) NOT NULL CHECK (percent >= 0 AND percent <= 100)
);

CREATE TABLE payment_methods (
    payment_method_id  SERIAL PRIMARY KEY,
    name               TEXT NOT NULL UNIQUE
);

CREATE TABLE organizations (
    org_id          SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    postal_index    VARCHAR(20),
    address         TEXT,
    phone           VARCHAR(50),
    fax             VARCHAR(50),
    inn             VARCHAR(20),
    corr_account    VARCHAR(34),
    bank            TEXT,
    checking_account VARCHAR(34),
    okonh           VARCHAR(20),
    okpo            VARCHAR(20),
    bik             VARCHAR(20),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT organizations_inn_unique UNIQUE (inn)
);

CREATE TABLE contracts (
    contract_id          SERIAL PRIMARY KEY,
    contract_number      TEXT NOT NULL,
    contract_date        DATE NOT NULL DEFAULT current_date,
    customer_org_id      INT NOT NULL REFERENCES organizations(org_id) ON DELETE RESTRICT,
    contractor_org_id    INT NOT NULL REFERENCES organizations(org_id) ON DELETE RESTRICT,
    contract_type_id     INT NOT NULL REFERENCES contract_types(contract_type_id),
    current_stage_id     INT REFERENCES execution_stages(stage_id),
    vat_id               INT REFERENCES vat_rates(vat_id),
    execution_date       DATE,
    subject              TEXT,
    note                 TEXT,
    is_active            BOOLEAN DEFAULT true,
    
    -- денормализованные данные, вычисляются триггерами:
    total_amount         NUMERIC(18,2) DEFAULT 0 CHECK (total_amount >= 0),
    paid_amount          NUMERIC(18,2) DEFAULT 0 CHECK (paid_amount >= 0),
    debt_amount          NUMERIC(18,2) DEFAULT 0 CHECK (debt_amount >= 0),
    UNIQUE (contract_number, customer_org_id) -- уникальность номера в рамках заказчика
);

CREATE TABLE contract_milestones (
    contract_id      INT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
    milestone_no     INT NOT NULL,
    milestone_date   DATE,
    stage_id         INT REFERENCES execution_stages(stage_id),
    amount           NUMERIC(18,2) NOT NULL CHECK (amount >= 0),
    advance_amount   NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (advance_amount >= 0),
    subject          TEXT,
    PRIMARY KEY (contract_id, milestone_no)
);

CREATE TABLE payments (
    payment_id          SERIAL PRIMARY KEY,
    contract_id         INT NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
    payment_date        DATE NOT NULL DEFAULT current_date,
    amount              NUMERIC(18,2) NOT NULL CHECK (amount > 0),
    payment_method_id   INT REFERENCES payment_methods(payment_method_id),
    payment_doc_number  TEXT
);

-- ============ Индексы ==============
CREATE INDEX idx_contracts_date ON contracts(contract_date);				-- для фильтрации по дате заключения договора
CREATE INDEX idx_contracts_customer ON contracts(customer_org_id);			-- часто ищем все договоры конкретного заказчика
CREATE INDEX idx_contracts_contractor ON contracts(contractor_org_id);		-- аналогично для исполнителя
CREATE INDEX idx_milestones_contract ON contract_milestones(contract_id);	-- выборка всех этапов по договору, 1:М
CREATE INDEX idx_payments_contract ON payments(contract_id);				-- аналогично для оплат по договору
CREATE INDEX idx_payments_date ON payments(payment_date);					-- для запросов по дате оплаты

-- ========== Представления ==========
-- по одной таблице
CREATE VIEW view_organizations AS
SELECT 
    org_id,
    name,
    postal_index,
    address,
    phone,
    inn,
    bank,
    created_at
FROM organizations;

-- многотабличное
CREATE VIEW view_contract_full AS
SELECT
    c.contract_id,
    c.contract_number,
    c.contract_date,
    cust.org_id   AS customer_id,
    cust.name     AS customer_name,
    contr.org_id  AS contractor_id,
    contr.name    AS contractor_name,
    ct.name       AS contract_type,
    es.name       AS current_stage,
    v.percent     AS vat_percent,
    c.total_amount,
    c.paid_amount,
    c.debt_amount,
    c.subject,
    c.note
FROM contracts c
LEFT JOIN organizations cust ON cust.org_id = c.customer_org_id
LEFT JOIN organizations contr ON contr.org_id = c.contractor_org_id
LEFT JOIN contract_types ct ON ct.contract_type_id = c.contract_type_id
LEFT JOIN execution_stages es ON es.stage_id = c.current_stage_id
LEFT JOIN vat_rates v ON v.vat_id = c.vat_id;

-- для отчёта - все этапы и оплаты по договорам 
CREATE VIEW view_contract_details AS
SELECT
    c.contract_id,
    c.contract_number,
    c.contract_date,
    cm.milestone_no,
    cm.milestone_date,
    cm.amount   AS milestone_amount,
    cm.advance_amount,
    p.payment_id,
    p.payment_date,
    p.amount    AS payment_amount
FROM contracts c
LEFT JOIN contract_milestones cm ON cm.contract_id = c.contract_id
LEFT JOIN payments p ON p.contract_id = c.contract_id;

-- контракты с существенным долгом
CREATE VIEW view_contracts_with_debt_over_10000 AS
SELECT
    c.contract_id,
    c.contract_number,
    c.customer_org_id,
    cust.name AS customer_name,
    c.total_amount,
    c.paid_amount,
    c.debt_amount
FROM contracts c
LEFT JOIN organizations cust ON cust.org_id = c.customer_org_id
WHERE c.debt_amount > 10000;

-- плановая оплата по этапам
CREATE VIEW view_milestones_summary_per_contract AS
SELECT
    cm.contract_id,
    c.contract_number,
    COUNT(*) AS milestones_count,
    SUM(cm.amount) AS milestones_total,
    SUM(cm.advance_amount) AS advances_total
FROM contract_milestones cm
JOIN contracts c ON c.contract_id = cm.contract_id
GROUP BY cm.contract_id, c.contract_number;

-- отчёт по поступлениям - суммарные оплаты по договорам
CREATE VIEW view_payments_summary_per_contract AS
SELECT
    p.contract_id,
    c.contract_number,
    COUNT(p.payment_id) AS payments_count,
    SUM(p.amount) AS payments_sum,
    MAX(p.payment_date) AS last_payment_date
FROM payments p
JOIN contracts c ON c.contract_id = p.contract_id
GROUP BY p.contract_id, c.contract_number
HAVING SUM(p.amount) > 0;

-- ========== Триггеры ==========

-- функция пересчёта total_amount - сумма по этапам
CREATE OR REPLACE FUNCTION recalc_contract_total_amount(p_contract_id INT) RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    sum_stage NUMERIC(18,2);
BEGIN
    SELECT COALESCE(SUM(amount),0) INTO sum_stage FROM contract_milestones WHERE contract_id = p_contract_id;
    UPDATE contracts SET total_amount = sum_stage WHERE contract_id = p_contract_id;
    -- пересчитаем debt
    UPDATE contracts
    SET debt_amount = GREATEST(total_amount - paid_amount, 0)
    WHERE contract_id = p_contract_id;
END; $$;

-- функция пересчёта paid_amount - сумма оплат
CREATE OR REPLACE FUNCTION recalc_contract_paid_amount(p_contract_id INT) RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    paid NUMERIC(18,2);
BEGIN
    SELECT COALESCE(SUM(amount),0) INTO paid FROM payments WHERE contract_id = p_contract_id;
    UPDATE contracts SET paid_amount = paid WHERE contract_id = p_contract_id;
    UPDATE contracts
    SET debt_amount = GREATEST(total_amount - paid_amount, 0)
    WHERE contract_id = p_contract_id;
END; $$;

-- триггеры на contract_milestones для вызова recalc_contract_total_amount
CREATE OR REPLACE FUNCTION trg_milestones_after_change() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    PERFORM recalc_contract_total_amount(COALESCE(NEW.contract_id, OLD.contract_id));
    RETURN NULL;
END; $$;

CREATE TRIGGER trg_milestones_after_insert
AFTER INSERT ON contract_milestones
FOR EACH ROW EXECUTE FUNCTION trg_milestones_after_change();

CREATE TRIGGER trg_milestones_after_update
AFTER UPDATE ON contract_milestones
FOR EACH ROW EXECUTE FUNCTION trg_milestones_after_change();

CREATE TRIGGER trg_milestones_after_delete
AFTER DELETE ON contract_milestones
FOR EACH ROW EXECUTE FUNCTION trg_milestones_after_change();

-- триггеры на payments для пересчёта paid_amount
CREATE OR REPLACE FUNCTION trg_payments_after_change() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    PERFORM recalc_contract_paid_amount(COALESCE(NEW.contract_id, OLD.contract_id));
    RETURN NULL;
END; $$;

CREATE TRIGGER trg_payments_after_insert
AFTER INSERT ON payments
FOR EACH ROW EXECUTE FUNCTION trg_payments_after_change();

CREATE TRIGGER trg_payments_after_update
AFTER UPDATE ON payments
FOR EACH ROW EXECUTE FUNCTION trg_payments_after_change();

CREATE TRIGGER trg_payments_after_delete
AFTER DELETE ON payments
FOR EACH ROW EXECUTE FUNCTION trg_payments_after_change();


-- ========== тест ==========
INSERT INTO contract_types (name) VALUES ('Подряд'), ('Агентский'), ('Лицензионный');
INSERT INTO execution_stages (name) VALUES ('Подготовка'), ('Выполнение'), ('Завершено');
INSERT INTO vat_rates (percent, description) VALUES (0.00, 'Без НДС'), (20.00, 'Стандартная ставка');
INSERT INTO payment_methods (name) VALUES ('Безнал'), ('Наличные'), ('Банковская карта');

INSERT INTO organizations (name, inn, address) VALUES
('ООО Заказчик', '1234567890', 'г. Ижевск, ул. Кирова, 1'),
('ИП Исполнитель', '0987654321', 'г. Ижевск, ул. Песочная, 2');

INSERT INTO contracts (contract_number, contract_date, customer_org_id, contractor_org_id, contract_type_id, vat_id, subject)
VALUES ('К-001/2025', '2025-09-01', 1, 2, 1, 2, 'Разработка ПО');

INSERT INTO contract_milestones (contract_id, milestone_no, milestone_date, stage_id, amount, advance_amount, subject)
VALUES
(1, 1, '2025-09-15', 2, 50000.00, 10000.00, 'Первый этап'),
(1, 2, '2025-10-15', 2, 70000.00, 0.00, 'Второй этап');

INSERT INTO payments (contract_id, payment_date, amount, payment_method_id, payment_doc_number)
VALUES (1, '2025-09-20', 10000.00, 1, 'П/П-100');


SELECT * FROM view_milestones_summary_per_contract
SELECT * FROM view_contract_details
SELECT * FROM contracts