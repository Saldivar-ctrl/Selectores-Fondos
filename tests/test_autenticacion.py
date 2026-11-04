import json
import unittest

from _comun import CasoAislado

from selectores_fondos.core import autenticacion
from selectores_fondos.core.configuracion import Configuracion

# Pocas iteraciones SOLO para que las pruebas sean rápidas
RAPIDO = 1000


class PruebasAutenticacion(CasoAislado):

    def test_contrasena_correcta_e_incorrecta(self):
        datos = autenticacion.crear_verificador("clave-123", RAPIDO)
        self.assertTrue(autenticacion.verificar("clave-123", datos))
        self.assertFalse(autenticacion.verificar("clave-124", datos))
        self.assertFalse(autenticacion.verificar("", datos))

    def test_la_sal_es_distinta_cada_vez(self):
        a = autenticacion.crear_verificador("misma", RAPIDO)
        b = autenticacion.crear_verificador("misma", RAPIDO)
        self.assertNotEqual(a["sal"], b["sal"])
        self.assertNotEqual(a["hash"], b["hash"])

    def test_no_se_guarda_en_texto_plano(self):
        autenticacion.establecer(self.config, "secreto-ñandú")
        self.config.guardar()
        texto = self.config.archivo.read_text(encoding="utf-8")
        self.assertNotIn("secreto-ñandú", texto)
        self.assertEqual(
            json.loads(texto)["autenticacion"]["algoritmo"], "pbkdf2_sha256")

    def test_persiste_entre_ejecuciones(self):
        autenticacion.establecer(self.config, "abcd1234")
        self.config.guardar()
        c = Configuracion.cargar(self.config.archivo)
        self.assertTrue(autenticacion.hay_contrasena(c))
        self.assertTrue(autenticacion.verificar("abcd1234", c.autenticacion))

    def test_datos_danados_o_vacios_devuelven_false(self):
        for datos in ({}, {"hash": "x"}, {"algoritmo": "otro"},
                      {"algoritmo": "pbkdf2_sha256", "sal": "%%", "hash": "x",
                       "iteraciones": 5},
                      {"algoritmo": "pbkdf2_sha256", "sal": "AA==", "hash": "AA==",
                       "iteraciones": 0},
                      None):
            self.assertFalse(autenticacion.verificar("x", datos))

    def test_contrasena_demasiado_corta(self):
        with self.assertRaises(ValueError):
            autenticacion.crear_verificador("abc", RAPIDO)

    def test_sin_contrasena_ni_sello_es_nueva(self):
        self.assertEqual(autenticacion.estado(self.config), "nueva")

    def test_con_contrasena_esta_ok(self):
        autenticacion.establecer(self.config, "abcd1234")
        self.config.guardar()
        self.assertEqual(autenticacion.estado(self.config), "ok")

    def test_borrar_el_verificador_bloquea_no_resetea(self):
        autenticacion.establecer(self.config, "abcd1234")
        self.config.guardar()
        # alguien borra las lineas de la contraseña en config.json
        self.config.autenticacion = {}
        self.config.guardar()
        c = Configuracion.cargar(self.config.archivo)
        self.assertEqual(autenticacion.estado(c), "bloqueada")

    def test_cambiar_el_hash_a_mano_bloquea(self):
        autenticacion.establecer(self.config, "abcd1234")
        self.config.guardar()
        self.config.autenticacion = autenticacion.crear_verificador("otra-clave", RAPIDO)
        self.assertEqual(autenticacion.estado(self.config), "bloqueada")

    def test_config_danado_con_sello_bloquea(self):
        autenticacion.establecer(self.config, "abcd1234")
        self.config.guardar()
        self.config.archivo.write_text("{roto", encoding="utf-8")
        c = Configuracion.cargar(self.config.archivo)
        self.assertEqual(autenticacion.estado(c), "bloqueada")

    def test_sello_ausente_con_verificador_se_recrea(self):
        autenticacion.establecer(self.config, "abcd1234")
        self.config.guardar()
        (self.config.archivo.parent / ".sello").unlink()
        self.assertEqual(autenticacion.estado(self.config), "ok")
        self.assertTrue((self.config.archivo.parent / ".sello").exists())

    def test_no_existe_comando_para_restablecer(self):
        self.assertFalse(hasattr(autenticacion, "borrar"))

    def test_el_repositorio_no_trae_contrasena_por_defecto(self):
        self.assertFalse(autenticacion.hay_contrasena(Configuracion()))

    def test_iteraciones_por_defecto_son_altas(self):
        self.assertGreaterEqual(autenticacion.ITERACIONES, 600_000)


if __name__ == "__main__":
    unittest.main()
