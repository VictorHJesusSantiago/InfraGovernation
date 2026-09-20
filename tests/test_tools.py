import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_module(relative_path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PasswordPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_module("05_politica_senha/app.py", "password_policy")

    def test_iso_policy_rejects_weak_password(self):
        valid, problems = self.policy.avaliar_senha("password", "iso27001")
        self.assertFalse(valid)
        self.assertTrue(problems)

    def test_nist_policy_accepts_long_non_common_password(self):
        valid, problems = self.policy.avaliar_senha("correct-horse-battery", "nist")
        self.assertTrue(valid)
        self.assertEqual([], problems)

    def test_compliant_config_has_no_findings(self):
        config = {
            "tamanho_minimo": 16,
            "exige_maiuscula": True,
            "exige_minuscula": True,
            "exige_numero": True,
            "exige_especial": True,
            "expiracao_dias": 90,
            "bloqueia_reuso_ultimas": 5,
            "bloqueia_senhas_comuns": True,
            "max_tentativas_login": 5,
        }
        self.assertEqual([], self.policy.validar_config(config, "iso27001"))


class BackupIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backup = load_module("10_backup_integridade/app.py", "backup_integrity")

    def test_backup_round_trip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            destination = Path(temp) / "destination"
            source.mkdir()
            (source / "data.txt").write_text("original", encoding="utf-8")

            archive, manifest = self.backup.executar_backup(str(source), str(destination))
            ok, differences = self.backup.validar_restauracao(archive, manifest)
            self.assertTrue(ok)
            self.assertEqual([], differences)

            data = json.loads(Path(manifest).read_text(encoding="utf-8"))
            data["arquivos"]["data.txt"] = "0" * 64
            Path(manifest).write_text(json.dumps(data), encoding="utf-8")
            ok, differences = self.backup.validar_restauracao(archive, manifest)
            self.assertFalse(ok)
            self.assertIn("HASH DIVERGENTE: data.txt", differences)


if __name__ == "__main__":
    unittest.main()
