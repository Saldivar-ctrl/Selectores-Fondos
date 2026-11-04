import os
import unittest
from pathlib import Path

from _comun import CasoAislado

from selectores_fondos.core import gestor_rutas


class PruebasRutas(CasoAislado):

    def test_expandir_con_espacios_y_acentos(self):
        ruta = gestor_rutas.expandir("~/Vídeos/mis fondos")
        self.assertEqual(ruta, Path.home() / "Vídeos" / "mis fondos")

    def test_videos_por_defecto_respeta_user_dirs(self):
        cfg = Path(os.environ["XDG_CONFIG_HOME"])
        cfg.mkdir(parents=True)
        (cfg / "user-dirs.dirs").write_text(
            'XDG_VIDEOS_DIR="$HOME/Vídeos"\n', encoding="utf-8")

        self.assertEqual(
            gestor_rutas.carpeta_videos_del_sistema(),
            Path.home() / "Vídeos")
        self.assertEqual(
            gestor_rutas.carpetas_videos(self.config),
            [Path.home() / "Vídeos" / "fondos"])

    def test_sin_user_dirs_usa_videos(self):
        self.assertEqual(
            gestor_rutas.carpeta_videos_del_sistema(), Path.home() / "Videos")

    def test_carpetas_configuradas_sin_repetir(self):
        a = self.dir / "a"
        a.mkdir()
        self.config.carpetas_videos = [str(a), str(a)]
        self.assertEqual(gestor_rutas.carpetas_videos(self.config), [a])

    def test_leer_bibliotecas_vdf(self):
        vdf = self.dir / "libraryfolders.vdf"
        vdf.write_text(
            '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"C:\\\\Program Files (x86)\\\\Steam"\n'
            '\t}\n\t"1"\n\t{\n\t\t"path"\t\t"D:\\\\Mis Juegos\\\\SteamLibrary"\n\t}\n}\n',
            encoding="utf-8")

        self.assertEqual(
            [str(p) for p in gestor_rutas.leer_bibliotecas_vdf(vdf)],
            ["C:\\Program Files (x86)\\Steam", "D:\\Mis Juegos\\SteamLibrary"])

    def test_vdf_inexistente(self):
        self.assertEqual(gestor_rutas.leer_bibliotecas_vdf(self.dir / "no"), [])

    def test_bibliotecas_y_carpetas_de_wallpaper_engine(self):
        biblioteca = self.dir / "Mi Steam"
        proyectos = biblioteca / "steamapps/common/wallpaper_engine/projects"
        (proyectos / "defaultprojects").mkdir(parents=True)
        (biblioteca / "steamapps/workshop/content/431960").mkdir(parents=True)
        self.config.carpetas_steam = [str(biblioteca)]

        rutas = gestor_rutas.carpetas_wallpaper_engine(self.config)
        self.assertIn(proyectos / "defaultprojects", rutas)
        self.assertIn(biblioteca / "steamapps/workshop/content/431960", rutas)
        self.assertEqual(
            gestor_rutas.instalaciones_wallpaper_engine(self.config),
            [biblioteca / "steamapps/common/wallpaper_engine"])

    def test_enlaces_simbolicos_no_duplican(self):
        real = self.dir / "real"
        (real / "steamapps/workshop/content/431960").mkdir(parents=True)
        enlace = self.dir / "enlace"
        enlace.symlink_to(real)
        self.config.carpetas_steam = [str(real), str(enlace)]

        self.assertEqual(
            len(gestor_rutas.carpetas_wallpaper_engine(self.config)), 1)


if __name__ == "__main__":
    unittest.main()
