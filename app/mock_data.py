"""演示用模拟数据：未配置 PayPal 沙盒凭据时，客户端以这份数据运行，保证 Demo 不依赖外部环境。"""

MOCK_SUBSCRIPTIONS = [
    {"id": "I-3N9821HKX7", "name": "Netflix Premium", "category": "视频娱乐", "monthly_amount": 68.00, "currency": "CNY", "status": "ACTIVE", "next_billing_date": "2026-11-02", "subscribed_since": "2023-06-14"},
    {"id": "I-5QX41LMK2P", "name": "iQIYI 黄金会员", "category": "视频娱乐", "monthly_amount": 25.00, "currency": "CNY", "status": "ACTIVE", "next_billing_date": "2026-10-28", "subscribed_since": "2024-01-08"},
    {"id": "I-7TR63VNDQ9", "name": "Spotify Premium", "category": "音乐", "monthly_amount": 19.99, "currency": "CNY", "status": "ACTIVE", "next_billing_date": "2026-11-05", "subscribed_since": "2022-09-30"},
    {"id": "I-9MVK55PLQ2", "name": "ChatGPT Plus", "category": "AI 工具", "monthly_amount": 145.00, "currency": "CNY", "status": "ACTIVE", "next_billing_date": "2026-11-01", "subscribed_since": "2024-03-21"},
    {"id": "I-2BCK88TNM4", "name": "Claude Pro", "category": "AI 工具", "monthly_amount": 145.00, "currency": "CNY", "status": "ACTIVE", "next_billing_date": "2026-11-08", "subscribed_since": "2024-07-12"},
    {"id": "I-6YDN33PQR7", "name": "Microsoft 365 家庭版", "category": "软件办公", "monthly_amount": 79.00, "currency": "CNY", "status": "ACTIVE", "next_billing_date": "2026-11-15", "subscribed_since": "2021-11-20"},
    {"id": "I-4GHW77KLT5", "name": "Keep 会员", "category": "健身", "monthly_amount": 15.00, "currency": "CNY", "status": "ACTIVE", "next_billing_date": "2026-10-27", "subscribed_since": "2025-02-01"},
    {"id": "I-1FTL99XZB6", "name": "Adobe Creative Cloud", "category": "软件办公", "monthly_amount": 98.00, "currency": "CNY", "status": "CANCELLED", "next_billing_date": None, "subscribed_since": "2020-05-17"},
]

# 最近 30 天内的模拟扣款流水（用于开销统计）
MOCK_TRANSACTIONS = [
    {"transaction_id": "TXN-20261002-001", "subscription_id": "I-3N9821HKX7", "name": "Netflix Premium", "amount": 68.00, "currency": "CNY", "date": "2026-10-02", "status": "COMPLETED"},
    {"transaction_id": "TXN-20261005-002", "subscription_id": "I-5QX41LMK2P", "name": "iQIYI 黄金会员", "amount": 25.00, "currency": "CNY", "date": "2026-10-05", "status": "COMPLETED"},
    {"transaction_id": "TXN-20261005-003", "subscription_id": "I-7TR63VNDQ9", "name": "Spotify Premium", "amount": 19.99, "currency": "CNY", "date": "2026-10-05", "status": "COMPLETED"},
    {"transaction_id": "TXN-20261001-004", "subscription_id": "I-9MVK55PLQ2", "name": "ChatGPT Plus", "amount": 145.00, "currency": "CNY", "date": "2026-10-01", "status": "COMPLETED"},
    {"transaction_id": "TXN-20261008-005", "subscription_id": "I-2BCK88TNM4", "name": "Claude Pro", "amount": 145.00, "currency": "CNY", "date": "2026-10-08", "status": "COMPLETED"},
    {"transaction_id": "TXN-20261015-006", "subscription_id": "I-6YDN33PQR7", "name": "Microsoft 365 家庭版", "amount": 79.00, "currency": "CNY", "date": "2026-10-15", "status": "COMPLETED"},
    {"transaction_id": "TXN-20261027-007", "subscription_id": "I-4GHW77KLT5", "name": "Keep 会员", "amount": 15.00, "currency": "CNY", "date": "2026-10-27", "status": "COMPLETED"},
    {"transaction_id": "TXN-20260901-008", "subscription_id": "I-1FTL99XZB6", "name": "Adobe Creative Cloud", "amount": 98.00, "currency": "CNY", "date": "2026-09-20", "status": "COMPLETED"},
]
