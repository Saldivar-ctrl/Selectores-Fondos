import json
import unittest

from _comun import CasoAislado

from selectores_fondos.core.configuracion import Configuracion


class PruebasConfiguracion(CasoAislado):

    def test_ausente_usa_valores_por_defecto(self):
        c = Configuracion.cargar(self.dir / "no_existe.json")
        self.assertEqual(c.backend, "auto")
        self.assertEqual(c.aviso, "")

    def test_guardar_y_cargar(self):
        self.config.carpetas_videos = ["/a b/Vídeos/fondos", "C:\\Mis Vídeos"]
        self.config.monitor = "1"
        self.config.guardar()

        c = Configuracion.cargar(self.config.archivo)
        self.assertEqual(c.carpetas_videos, ["/a b/Vídeos/fondos", "C:\\Mis Vídeos"])
        self.assertEqual(c.monitor, "1")

    def test_json_danado_no_rompe(self):
        self.config.archivo.parent.mkdir(parents=True)
        self.config.archivo.write_text("{esto no es json", encoding="utf-8")

        c = Configuracion.cargar(self.config.archivo)
        self.assertIn("No se pudo leer", c.aviso)
        self.assertEqual(c.backend, "auto")

    def test_valores_de_tipo_incorrecto_se_ignoran(self):
        self.config.archivo.parent.mkdir(parents=True)
        self.config.archivo.write_text(
            json.dumps({"backend": "inventado", "carpetas_videos": "no-lista",
                        "modo_oculto_habilitado": "si", "interfaz": 7}),
            encoding="utf-8")

        c = Configuracion.cargar(self.config.archivo)
        self.assertEqual(c.backend, "auto")
        self.assertEqual(c.carpetas_videos, [])
        self.assertTrue(c.modo_oculto_habilitado)
        self.assertEqual(c.interfaz, "circular")

    def test_claves_desconocidas_se_ignoran(self):
        self.config.archivo.parent.mkdir(parents=True)
        self.config.archivo.write_text(json.dumps({"otra": 1}), encoding="utf-8")
        self.assertEqual(Configuracion.cargar(self.config.archivo).backend, "auto")

    def test_no_guarda_campos_internos(self):
        self.config.guardar()
        datos = json.loads(self.config.archivo.read_text(encoding="utf-8"))
        self.assertNotIn("archivo", datos)
        self.assertNotIn("aviso", datos)

    def test_escritura_atomica_no_deja_temporales(self):
        self.config.guardar()
        restos = [p.name for p in self.config.archivo.parent.iterdir()
                  if p.name != "config.json"]
        self.assertEqual(restos, [])

    def test_historial_y_fondo_anterior(self):
        c = self.config
        c.registrar_aplicado("/a.mp4")
        self.assertEqual(c.fondo_anterior(), "")
        c.registrar_aplicado("/b.mp4")
        self.assertEqual(c.fondo_anterior(), "/a.mp4")
        c.registrar_aplicado("/c.mp4")
        self.assertEqual(c.historial, ["/b.mp4", "/a.mp4"])
        # volver al anterior intercambia los papeles
        c.registrar_aplicado("/b.mp4")
        self.assertEqual(c.ultimo_fondo, "/b.mp4")
        self.assertEqual(c.fondo_anterior(), "/c.mp4")

    def test_carpeta_privados_junto_a_la_config(self):
        efectivas = self.config.carpetas_ocultas_efectivas()
        self.assertTrue(efectivas[0].endswith("privados"))
        self.assertIn(str(self.config.archivo.parent), efectivas[0])


if __name__ == "__main__":
    unittest.main()
