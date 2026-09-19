-- Warehouse Management API - PostgreSQL schema derived from data/*.json
-- Shape only: tables, columns, keys and foreign keys (no data load).

CREATE TABLE warehouse (
    id             INTEGER PRIMARY KEY,
    code           VARCHAR,
    name           VARCHAR,
    address        VARCHAR,
    city           VARCHAR,
    zip_code       VARCHAR,
    province       VARCHAR,
    country        VARCHAR,
    contact_name   VARCHAR,
    contact_phone  VARCHAR,
    contact_email  VARCHAR,
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP
);

CREATE TABLE location (
    id             INTEGER PRIMARY KEY,
    warehouse_id   INTEGER REFERENCES warehouse(id),
    code           VARCHAR,
    name           VARCHAR,
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP
);

CREATE TABLE client (
    id             INTEGER PRIMARY KEY,
    name           VARCHAR,
    address        VARCHAR,
    city           VARCHAR,
    zip_code       VARCHAR,
    province       VARCHAR,
    country        VARCHAR,
    contact_name   VARCHAR,
    contact_phone  VARCHAR,
    contact_email  VARCHAR,
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP
);

CREATE TABLE supplier (
    id             INTEGER PRIMARY KEY,
    code           VARCHAR,
    name           VARCHAR,
    address        VARCHAR,
    city           VARCHAR,
    zip_code       VARCHAR,
    province       VARCHAR,
    country        VARCHAR,
    contact_name   VARCHAR,
    phone_number   VARCHAR,
    reference      VARCHAR,
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP
);

CREATE TABLE item_line (
    id             INTEGER PRIMARY KEY,
    name           VARCHAR,
    description    VARCHAR,
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP
);

CREATE TABLE item_group (
    id             INTEGER PRIMARY KEY,
    name           VARCHAR,
    description    VARCHAR,
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP
);

CREATE TABLE item_type (
    id             INTEGER PRIMARY KEY,
    name           VARCHAR,
    description    VARCHAR,
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP
);

CREATE TABLE item (
    id               INTEGER PRIMARY KEY,
    code             VARCHAR,
    description      VARCHAR,
    barcode          VARCHAR,
    model_number     VARCHAR,
    commodity_code   INTEGER,
    unit_weight      FLOAT,
    item_line_id     INTEGER REFERENCES item_line(id),
    item_group_id    INTEGER REFERENCES item_group(id),
    item_type_id     INTEGER REFERENCES item_type(id),
    min_purchase_qty INTEGER,
    case_size        INTEGER,
    packaging_type   VARCHAR,
    order_multiple   INTEGER,
    supplier_id      INTEGER REFERENCES supplier(id),
    supplier_sku     VARCHAR,
    created_at       TIMESTAMP,
    updated_at       TIMESTAMP
);

CREATE TABLE inventory (
    item_id             INTEGER REFERENCES item(id),
    location_id         INTEGER REFERENCES location(id),
    quantity_on_hand    INTEGER,
    quantity_expected   INTEGER,
    quantity_ordered    INTEGER,
    quantity_allocated  INTEGER,
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP,
    PRIMARY KEY (item_id, location_id)
);

CREATE TABLE "order" (
    id                  INTEGER PRIMARY KEY,
    client_id           INTEGER REFERENCES client(id),
    order_date          TIMESTAMP,
    request_date        TIMESTAMP,
    reference           VARCHAR,
    customer_po_number  VARCHAR,
    order_status        VARCHAR,
    shipping_notes      VARCHAR,
    warehouse_id        INTEGER REFERENCES warehouse(id),
    ship_to_client_id   INTEGER REFERENCES client(id),
    bill_to_client_id   INTEGER REFERENCES client(id),
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP
);

CREATE TABLE order_item (
    id          INTEGER PRIMARY KEY,
    order_id    INTEGER REFERENCES "order"(id),
    item_id     INTEGER REFERENCES item(id),
    amount      INTEGER,
    unit_price  FLOAT
);

CREATE TABLE shipment (
    id               INTEGER PRIMARY KEY,
    reference        VARCHAR,
    order_id         INTEGER REFERENCES "order"(id),
    shipment_date    TIMESTAMP,
    shipment_type    VARCHAR,
    shipment_status  VARCHAR,
    carrier_name     VARCHAR,
    shipping_method  VARCHAR,
    payment_type     VARCHAR,
    created_at       TIMESTAMP,
    updated_at       TIMESTAMP
);

CREATE TABLE shipment_item (
    id           INTEGER PRIMARY KEY,
    shipment_id  INTEGER REFERENCES shipment(id),
    item_id      INTEGER REFERENCES item(id),
    amount       INTEGER
);

CREATE TABLE transfer (
    id                INTEGER PRIMARY KEY,
    reference         VARCHAR,
    from_location_id  INTEGER REFERENCES location(id),
    to_location_id    INTEGER REFERENCES location(id),
    transfer_status   VARCHAR,
    created_at        TIMESTAMP,
    updated_at        TIMESTAMP
);

CREATE TABLE transfer_item (
    id           INTEGER PRIMARY KEY,
    transfer_id  INTEGER REFERENCES transfer(id),
    item_id      INTEGER REFERENCES item(id),
    amount       INTEGER
);

-- Standalone: API-key based access config, not linked to the domain model
CREATE TABLE "user" (
    api_key          VARCHAR PRIMARY KEY,
    app              VARCHAR,
    endpoint_access  JSONB
);
