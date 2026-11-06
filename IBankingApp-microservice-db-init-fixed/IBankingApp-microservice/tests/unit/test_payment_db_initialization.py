from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_payment_api_and_worker_do_not_create_schema_on_import():
    main = (ROOT / "backend/payment-service/app/main.py").read_text()
    worker = (ROOT / "backend/payment-service/app/worker.py").read_text()
    init = (ROOT / "backend/payment-service/app/init_db.py").read_text()
    assert "Base.metadata.create_all" not in main
    assert "from app.main import" in worker
    assert "Base.metadata.create_all" in init
    assert "pg_advisory_lock" in init


def test_compose_starts_payment_after_database_init():
    for filename in ("docker-compose.yml", "docker-compose.e2e.yml"):
        compose = (ROOT / filename).read_text()
        init = compose.split("  payment-db-init:\n", 1)[1].split("  payment-service:\n", 1)[0]
        assert 'command: ["python", "-m", "app.init_db"]' in init
        assert "db-bootstrap:" in init
        assert "condition: service_completed_successfully" in init
        for service, next_service in (("payment-service", "payment-worker"), ("payment-worker", "notification-service")):
            section = compose.split(f"  {service}:\n", 1)[1].split(f"  {next_service}:\n", 1)[0]
            assert "payment-db-init:\n        condition: service_completed_successfully" in section
