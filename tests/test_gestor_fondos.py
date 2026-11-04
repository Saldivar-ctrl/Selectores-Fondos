import json
import unittest

from _comun import CasoAislado

from selectores_fondos.core.gestor_fondos import GestorFondos
from selectores_fondos.platforms.base import Backend, ErrorBackend


class BackendFalso(Backend):
    id = "falso"
    usa_wallpaper_engine = True

    def __init__(self, config):
        super().__init__(config)
        self.aplicados = []

    def filtrar_registrados(self, fondos):
        return fondos

    def aplicar(self, fondo):
        self.aplicados.append(fondo.path)
        return "ok"


def crear_proyecto(biblioteca, carpeta, numero, titulo, archivo="video.mp4"):
    d = biblioteca / "steamapps/workshop/content/431960" / numero
    d.mkdir(parents=True)
    (d / archivo).write_bytes(b"x")
    (d / "preview.jpg").write_bytes(b"x")
    (d / "project.json").write_text(json.dumps(
        {"file": archivo, "preview": "preview.jpg", "title": titulo,
         "type": "video"}), encoding="utf-8")
    return d


class PruebasGestor(CasoAislado):

    def setUp(self):
        super().setUp()
        self.videos = self.dir / "Vídeos con espacio" / "fondos"
        self.videos.mkdir(parents=True)
        for n in ("uno.mp4", "dos.webm", "tres.png", "notas.txt"):
            (self.videos / n).write_bytes(b"x")

        self.steam = self.dir / "Steam"
        crear_proyecto(self.steam, None, "111", "Playa")
        crear_proyecto(self.steam, None, "222", "Secreto")

        self.config.carpetas_videos = [str(self.videos)]
        self.config.carpetas_steam = [str(self.steam)]
        self.backend = BackendFalso(self.config)
        self.gestor = GestorFondos(self.config, self.backend)

    def titulos(self, **kw):
        return [f.title for f in self.gestor.listar(**kw)]

    def test_lista_archivos_y_proyectos_ignorando_otros_formatos(self):
        self.assertEqual(self.titulos(), ["dos", "tres", "uno", "Playa", "Secreto"])

    def test_oculta_por_numero_de_carpeta(self):
        self.config.fondos_ocultos = ["222"]
        self.assertNotIn("Secreto", self.titulos())
        self.assertIn("Secreto", self.titulos(mostrar_ocultos=True))

    def test_oculta_por_titulo_y_por_nombre_de_archivo(self):
        self.config.fondos_ocultos = ["secreto", "uno.mp4"]
        t = self.titulos()
        self.assertNotIn("Secreto", t)
        self.assertNotIn("uno", t)

    def test_oculta_con_entrada_vacia_en_carpeta_privada(self):
        privados = self.config.archivo.parent / "privados"
        privados.mkdir(parents=True)
        (privados / "222").mkdir()          # carpeta vacía con el número
        (privados / "dos.webm").write_bytes(b"")  # archivo vacío con el nombre
        t = self.titulos()
        self.assertNotIn("Secreto", t)
        self.assertNotIn("dos", t)
        self.assertEqual(len(self.titulos(mostrar_ocultos=True)), 5)

    def test_marca_como_oculto(self):
        self.config.fondos_ocultos = ["222"]
        f = [x for x in self.gestor.listar(mostrar_ocultos=True) if x.id == "222"][0]
        self.assertTrue(f.oculto)

    def test_el_proyecto_guarda_project_json_y_vista_previa(self):
        f = [x for x in self.gestor.listar() if x.id == "111"][0]
        self.assertTrue(f.proyecto.endswith("project.json"))
        self.assertTrue(f.preview.endswith("preview.jpg"))
        self.assertTrue(f.path.endswith("video.mp4"))

    def test_aplicar_guarda_historial_y_restaura(self):
        a, b = self.gestor.listar()[0], self.gestor.listar()[1]
        self.gestor.aplicar(a)
        self.gestor.aplicar(b)
        self.assertEqual(self.config.fondo_anterior(), a.path)

        self.gestor.restaurar_anterior()
        self.assertEqual(self.backend.aplicados[-1], a.path)
        self.assertEqual(self.config.ultimo_fondo, a.path)
        # y quedó guardado en disco
        self.assertTrue(self.config.archivo.exists())

    def test_restaurar_sin_historial_da_error_claro(self):
        with self.assertRaises(ErrorBackend):
            self.gestor.restaurar_anterior()

    def test_proyecto_roto_se_ignora(self):
        d = self.steam / "steamapps/workshop/content/431960/333"
        d.mkdir()
        (d / "project.json").write_text("{roto", encoding="utf-8")
        self.assertEqual(len(self.titulos()), 5)

    def test_carpeta_inexistente_no_rompe(self):
        self.config.carpetas_videos = [str(self.dir / "nada")]
        self.assertEqual(self.titulos(), ["Playa", "Secreto"])

    def test_backend_sin_wallpaper_engine_no_lista_proyectos(self):
        self.backend.usa_wallpaper_engine = False
        self.assertEqual(self.titulos(), ["dos", "tres", "uno"])


if __name__ == "__main__":
    unittest.main()
