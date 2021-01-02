# -*- coding: utf-8 -*-
from os.path import exists, dirname, abspath
from configparser import ConfigParser, SectionProxy
from time import time
from sqlite3 import connect

import pygame
import pygame_gui

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()
pygame.mixer.init()

SETTINGS_FILE = 'settings.ini'


class SpriteError(Exception):
    '''Can't find sprite file'''
    __slots__ = ['text']

    def __init__(self):
        super().__init__()
        self.text = 'Не удаётся найти файл спрайта'


class Sprite:
    '''Base sprite class

    Methods:
        *set_group - Add skin to group
        *to_spawn - Move sprite to start position
        *teleport - Teleport sprite to selected position
    '''
    __slots__ = ['start_position', 'hit_points', 'skin', 'settings',
                 'skin_group', 'width', 'height', 'folder_path', 'skin_name']

    def __init__(self, position: list, hit_points: int, skin_name: str,
                 folder_path: str):
        self.start_position: list = position
        self.hit_points: int = hit_points
        self.skin_name: str = skin_name
        self.folder_path: str = folder_path
        self.settings: dict = Settings(SETTINGS_FILE).settings

    def setup(self, full_file_path: str) -> None:
        self.skin: pygame.sprite.Sprite = self.set_skin(full_file_path)
        self.width: int = self.skin.image.get_width()
        self.height: int = self.skin.image.get_height()

    def set_group(self) -> None:
        self.skin_group = pygame.sprite.Group()
        self.skin_group.add(self.skin)

    def to_spawn(self) -> None:
        self.teleport(self.start_position)

    def teleport(self, position: list) -> None:
        self.skin.x, self.skin.y = position

    def full_file_path(self, skin_path: str) -> str:
        game_path: str = self.settings['path']
        sprite_folder = f'{game_path}/{self.folder_path}'
        full_skin_path = f'{sprite_folder}/{self.skin_name}/{skin_path}'
        return full_skin_path

    def set_skin(self, skin_path: str) -> pygame.sprite.Sprite:
        full_skin_path = self.full_file_path(skin_path)
        if not exists(full_skin_path):
            raise SpriteError
        sprite = pygame.sprite.Sprite()
        sprite.image = pygame.image.load(full_skin_path).convert_alpha()
        sprite.rect = sprite.image.get_rect()
        sprite.rect.x, sprite.rect.y = self.start_position
        return sprite

    def change_skin(self, skin_path: str) -> pygame.sprite.Sprite:
        full_skin_path = self.full_file_path(skin_path)
        if not exists(full_skin_path):
            raise SpriteError
        current_position = (self.skin.rect.x, self.skin.rect.y)
        self.skin.image = pygame.image.load(full_skin_path)
        self.skin.rect = self.skin.image.get_rect()
        self.skin.rect.x, self.skin.rect.y = current_position

    def is_in_window(self, position: list) -> bool:
        x: int = position[0]
        y: int = position[1]
        if x not in range(self.settings['window_size'][0] + self.width):
            return False
        if y not in range(self.settings['window_size'][1] + self.height):
            return False
        return True


class DataBase:
    __slots__ = ['sound_db_path', 'selected_db_path', 'font_db_path',
                 'text_db_path']

    def __init__(self, db_folder_path: str):
        self.sound_db_path: str = f'{db_folder_path}/sounds.db'
        self.font_db_path: str = f'{db_folder_path}/fonts.db'
        self.text_db_path: str = f'{db_folder_path}/text.db'
        self.selected_db_path = self.sound_db_path

    def execute(self, command: str) -> str:
        with connect(self.selected_db_path) as database:
            cur = database.cursor()
            result: str = cur.execute(command).fetchall()
        return result

    def get_text(self) -> dict:
        self.selected_db_path = self.text_db_path
        result = self.execute('SELECT *\nFROM en')[0]
        decryptor = {0: 'play', 1: 'shop', 2: 'faq', 3: 'settings',
                     4: 'faq_text'}
        return {decryptor[index]: title for index, title in enumerate(result)}

    def get_sounds(self) -> list([tuple, tuple, tuple, ...]):
        self.selected_db_path = self.sound_db_path
        return self.execute('SELECT *\nFROM sounds')

    def get_fonts(self, name) -> str:
        self.selected_db_path = self.font_db_path
        result = self.execute(
            f'SELECT path\nFROM fonts\nWHERE name = "{name}"')
        return result[0][0]


class Sounds:
    __slots__ = ['database', 'sounds']

    def __init__(self, database):
        self.database = DataBase(database)
        self.sounds = self.get_sounds()

    def get_sounds(self) -> dict:
        sounds = self.database.get_sounds()
        return {name: {'path': path,
                       'sound': pygame.mixer.Sound(path)}
                for (name, path) in sounds}

    def play(self, name, loops=1) -> None:
        self.sounds[name]['sound'].play(loops)

    def stop(self, name):
        self.sounds[name]['sound'].stop()

    def stop_all(self) -> None:
        for name in self.sounds:
            self.sounds[name]['sound'].stop()


class Settings:
    __slots__ = ['settings_path', 'settings_parser', 'settings']

    def __init__(self, settings_file_name: str):
        self.settings_path: str = f'./{settings_file_name}'
        self.settings_parser: ConfigParser = ConfigParser()
        self.settings = self.all_settings()

    def all_settings(self) -> dict:
        self.settings_parser.read(self.settings_path, encoding='utf-8')
        dirty_settings: SectionProxy = self.settings_parser[
            'ChristmasAdventures']
        fps = int(dirty_settings['fps'])
        skin: str = dirty_settings['skin']
        backround_color: str = dirty_settings['backround_color']
        window_size = list(
            map(int, dirty_settings['window_size'].split('x')))
        path: str = dirname(abspath(__file__))
        return {'fps': fps, 'path': path,
                'background_color': backround_color,
                'window_size': window_size,
                'skin': skin,
                '_settings_path': self.settings_path}
    
    def save(self, new_settings: dict) -> None:
        for key in new_settings:
            self.settings_parser.set(
                'ChristmasAdventures', key, new_settings[key])
        with open(self.settings_path, 'w', encoding='utf-8') as settings_file:
            self.settings_parser.write(settings_file)

class Player(Sprite):
    __slots__ = ['skin', 'jump_count', 'jump_time', 'last_stand_func_call',
                 'state', 'sounds', 'skins', 'jump_start']

    def __init__(self, position: list, hp: int, skin_name: str):
        super().__init__(position, hp, skin_name, 'assets/sprites/santa')
        self.skin: pygame.sprite.Sprite = self.set_player_skin('stand')
        self.setup(self.get_skins()['stand'])
        self.skins = self.get_skins()
        self.jump_count, self.jump_time = 10, 0.1
        self.last_stand_func_call = 0
        self.jump_start = 0
        self.state: dict = {'sit': False, 'jump': False, 'flip': False,
                            'flip_counter': 0}
        db_path: str = self.settings['path'] + '/assets/database/'
        self.sounds = Sounds(db_path)
        self.to_spawn()
        self.set_group()

    def set_player_skin(self, skin_type: str = '') -> pygame.sprite.Sprite:
        return self.set_skin(self.get_skins()[skin_type])

    def change_player_skin(self, skin_type: str = '') -> None:
        return self.change_skin(self.get_skins()[skin_type])

    def get_skins(self) -> dict:
        skin_file_name_stand = f'santa_{self.skin_name}_skin.png'
        skin_file_name_sit = f'santa_{self.skin_name}_sit_skin.png'
        skin_file_name_jump = f'santa_{self.skin_name}_jump_skin.png'
        skins = {'stand': skin_file_name_stand,
                 'sit': skin_file_name_sit,
                 'jump': skin_file_name_jump}
        return skins

    def die(self) -> None:
        self.hit_points -= 1
        self.to_spawn()
        self.sounds.stop('step')
        self.sounds.play('die')

    def turn(self, direction: str) -> None:
        if not self.state['flip'] and direction == 'left':
            self.flip()
        if self.state['flip'] and direction == 'right':
            self.flip()

    def move(self, direction: str) -> None:
        i = 1 if self.state['jump'] else 5
        if self.state['sit']:
            return self.turn(direction)
        elif direction == 'right':
            if self.is_in_window([self.skin.rect.x + i, self.skin.rect.y]):
                self.skin.rect.x += i
            else:
                return
            if self.state['flip']:
                self.flip()
        elif direction == 'left':
            if self.is_in_window([self.skin.rect.x - i, self.skin.rect.y]):
                self.skin.rect.x -= i
            else:
                return
            if not self.state['flip']:
                self.flip()
        self.sounds.play('step')

    def flip(self) -> None:
        flip = pygame.transform.flip
        self.skin.image = flip(self.skin.image, True, False)
        self.state['flip'] = not self.state['flip']
        self.state['flip_counter'] += 1

    def fix_jump(self) -> None:
        pygame.key.set_repeat(1, 1)
        if self.state['jump']:
            return
        self.state['jump'] = True
        self.jump_start = self.skin.rect.y
        self.change_player_skin('jump')
        self.sounds.stop_all()
        self.sounds.play('jump')

    def sit(self) -> None:
        if not (self.state['sit'] or self.state['jump']):
            self.state['sit'] = True
            self.change_player_skin('sit')
            if self.state['flip']:
                self.flip()

    def stand(self) -> None:
        if self.state['sit']:
            self.state['sit'] = False
            self.last_stand_func_call = time()
            self.change_player_skin('stand')
            if self.state['flip']:
                self.flip()
        else:
            if time() - self.last_stand_func_call > 0.3:
                self.fix_jump()

    def jump(self) -> None:
        if self.jump_count >= -10:
            speed_direction = -1 if self.jump_count < 0 else 1
            if self.state['flip']:
                self.flip()
            self.skin.rect.y -= speed_direction * \
                ((self.jump_count ** 2) / 2)
            self.jump_count -= 1
        else:
            self.state['jump'] = False
            self.state['sit'] = True
            pygame.key.set_repeat(1, 100)
            pygame.mixer.unpause()
            self.skin.rect.y = self.jump_start
            self.jump_count = 10
            self.stand()
            




class Window:
    __slots__ = ['settings', 'fps', 'mode', 'background_filler',
                 'text_filler', 'clock', 'screen', 'gui_manager',
                 'database', 'gui_tools']

    def __init__(self, settings: dict, mode: str):
        pygame.event.set_allowed(
            [pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN,
             pygame.USEREVENT, pygame.MOUSEBUTTONUP])
        pygame.key.set_repeat(1, 100)
        self.settings: dict = settings
        self.gui_tools = GUItools(settings)
        self.gui_manager = self.gui_tools.gui_manager
        db_path = f'{self.settings["path"]}/assets/database/'
        self.database = DataBase(db_path)
        self.fps = self.settings['fps']
        self.mode = mode
        background_path = self.settings['path'] + \
            '/assets/sprites/background/background.png'
        self.background_filler = pygame.image.load(background_path)
        self.clock: pygame.time.Clock = pygame.time.Clock()
        icon_path = '/assets/sprites/icons/window_icons/icon_standart.png'
        icon = pygame.image.load(self.settings['path'] + icon_path)
        pygame.display.set_icon(icon)
        self.screen = self.get_screen(
            'Christmas Adventures', self.settings['window_size'])

    def get_screen(self, title: str, window_size: list) -> pygame.Surface:
        flags = pygame.DOUBLEBUF
        screen: pygame.Surface = pygame.display.set_mode(window_size, flags)
        screen.set_alpha(None)
        pygame.display.set_caption(title)
        return screen


class Level(Window):
    __slots__ = ['santa']

    def __init__(self, settings: dict):
        super().__init__(settings, mode='level')
        load = pygame.image.load
        relative_background_path = '/assets/sprites/background/background.png'
        background_path = f'{self.settings["path"]}{relative_background_path}'
        self.background_filler = load(background_path)
        self.santa: Player = Player(
            [0, self.settings['window_size'][1] - 16], 2,
            self.settings['skin'])

    def game_cycle(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.event_handler(event)
            if self.santa.state['jump']:
                self.santa.jump()
            self.clock.tick(self.fps)
            self.screen.blit(self.background_filler, [0, 0])
            self.draw()
            pygame.display.update()
        pygame.quit()

    def event_handler(self, event: pygame.event) -> None:
        if event.type == pygame.KEYDOWN:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_RIGHT]:
                self.santa.move('right')
            if keys[pygame.K_LEFT]:
                self.santa.move('left')
            if keys[pygame.K_DOWN]:
                self.santa.sit()
            if keys[pygame.K_UP]:
                self.santa.stand()

    def draw(self) -> None:
        self.santa.skin_group.draw(self.screen)


class SettingsWindow(Window):

    def __init__(self, settings: dict):
        super().__init__(settings, mode='settings')
        sprites = f'{self.settings["path"]}/assets/sprites/'        
        background_path = f'{sprites}/background/main_window_background.png'
        self.background_filler = pygame.image.load(background_path)

    def game_cycle(self) -> None:
        running = True
        while running:
            time_delta = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                running = self.event_handler(event)
            self.gui_tools.gui_manager.process_events(event)
            self.clock.tick(self.fps)
            self.screen.blit(self.background_filler, [0, 0])
            self.gui_tools.gui_manager.draw_ui(self.screen)
            self.gui_tools.gui_manager.update(time_delta)
            self.draw()
            pygame.display.update()

    def draw(self):
        self.gui_tools.draw_background_text(self.screen)

    def event_handler(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.USEREVENT and self.gui_tools.is_button_event(event):
            button_name = self.gui_tools.get_button_name(event.ui_element)
            if button_name == 'no':
                pass
            elif button_name == 'yes':
                pass
        return True

class GUItools:
    def __init__(self, settings: dict):
        self.settings = settings
        self.text_filler = (255, 255, 255)        
        db_path = f'{self.settings["path"]}/assets/database/'
        self.database = DataBase(db_path)
        self.texts = self.database.get_text()
        self.gui_manager = pygame_gui.UIManager(self.settings['window_size'])
        font_path = f"{self.settings['path']}/{self.database.get_fonts('christmas')}"
        self.christmas_font = pygame.font.Font(font_path, 50)
        self.main_heading = self.get_background_text('Christmas Adventures')        
        self.buttons = self.get_buttons()

    def get_buttons_images(self, images_name_list) -> dict:
        gui_path = self.settings['path'] + '/assets/sprites/icons/gui/'
        load = pygame.image.load
        images = {name: {
            'normal_image': load(f'{gui_path}{name}.png'),
            'hovered_image': load(f'{gui_path}{name}_pressed.png')}
            for name in images_name_list}
        return images

    def load_icon(self, icon_path) -> pygame.Surface:
        return pygame.transform.scale(icon_path, [50, 50])

    def is_button_event(self, event):
        if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element.text == '':
                for button_name in self.buttons:
                    if event.ui_element == self.buttons[button_name]:
                        return True
        return False    

    def draw_button_label(self, button_x_position, space, label) -> None:
        label_x = button_x_position + 46
        label_y = self.settings['window_size'][1] - 55
        label_w = space - 46
        label_h = 50
        label_rect = pygame.Rect((label_x, label_y), (label_w, label_h))
        label = pygame_gui.elements.UIButton(
            relative_rect=label_rect,
            text=label.capitalize(),
            manager=self.gui_manager)
        main_color = label.colours['normal_bg']
        for theme in label.colours:
            if 'text' not in theme:
                label.colours[theme] = main_color
        label.rebuild()

    def get_buttons(self) -> dict:
        images_name_list = ['settings', 'faq', 'shop', 'play']
        images = self.get_buttons_images(images_name_list)
        buttons = {}
        space = self.settings['window_size'][0] // len(images_name_list)
        for index, name in enumerate(images_name_list):
            button = self.build_button(index, space, name, images)
            buttons[name] = button
        return buttons

    def build_button(self, index, space, name,
                     images) -> pygame_gui.elements.ui_button:
        button_rect = pygame.Rect((5 + index * space,
                                   self.settings['window_size'][1] - 55),
                                  (50, 50))
        self.draw_button_label(5 + index * space, space, self.texts[name])
        button = globals()[name] = None
        button = pygame_gui.elements.UIButton(
            relative_rect=button_rect, text='', manager=self.gui_manager)
        settings_icon = self.load_icon(images[name]['normal_image'])
        settings_pressed_icon = self.load_icon(images[name]['hovered_image'])
        button.normal_image = button.selected_image = settings_icon
        button.hovered_image = settings_pressed_icon
        button.rebuild()
        return button 
    
    def get_background_text(self, text: str) -> (pygame.font.Font.render,
                                                 (int, int)):
        text = self.christmas_font.render(text,
                                          True, self.text_filler)
        text_x = self.settings['window_size'][0] // 2 - \
            text.get_width() // 2
        text_y = 20
        return text, (text_x, text_y)   


    def draw_background_text(self, screen) -> None:
        screen.blit(*self.main_heading)

    def get_button_name(self, button):
        for button_name in self.buttons:
            if button == self.buttons[button_name]:
                return button_name
        return ''
    
    def is_button_event(self, event):
        if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element.text == '':
                for button_name in self.buttons:
                    if event.ui_element == self.buttons[button_name]:
                        return True
        return False    
    
    def show_message(self, title: str, text: str):
        window = pygame_gui.windows.UIMessageWindow(
            rect=pygame.Rect(
                (170, 100), (400, 300)),
            window_title=title,
            html_message=text,
            manager=self.gui_manager)
        window.dismiss_button.text = 'Ok'
        window.dismiss_button.rebuild()
        return window        

        

class MainWindow(Window):
    __slots__ = ['christmas_font', 'background_filler',
                 'buttons', 'texts']

    def __init__(self, settings: dict):
        super().__init__(settings, mode='main_window')
        sprites = f'{self.settings["path"]}/assets/sprites/'
        background_path = f'{sprites}/background/main_window_background.png'
        self.background_filler = pygame.image.load(background_path)

    def draw(self) -> None:
        self.gui_tools.draw_background_text(self.screen)

    def show_faq(self):
        window = self.gui_tools.show_message(
            title='FAQ',
            text=self.gui_tools.texts['faq_text'])
        return window

    def game_cycle(self) -> None:
        running = True
        faq = None
        while running:
            time_delta = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                running, faq = self.event_handler(event, running, faq)
            if faq != None and (faq.dismiss_button.pressed
                                or faq.close_window_button.pressed):
                faq.kill()
            self.gui_tools.gui_manager.process_events(event)
            self.clock.tick(self.fps)
            self.screen.blit(self.background_filler, [0, 0])
            self.draw()
            self.gui_tools.gui_manager.draw_ui(self.screen)
            self.gui_tools.gui_manager.update(time_delta)
            pygame.display.update()

    def event_handler(self, event, running, faq=None) -> (bool, None):
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.USEREVENT and self.gui_tools.is_button_event(
                event):
            button_name = self.gui_tools.get_button_name(event.ui_element)
            if button_name == 'faq':
                faq = self.show_faq()
            elif button_name == 'settings':
                self.mode = 'settings'
                running = False
            elif button_name == 'play':
                self.mode = 'level'
                running = False
        return (running, faq)


class Game:
    __slots__ = ['game']

    def __init__(self, settings: dict, mode: str):
        if mode == 'level':
            self.game = Level(settings)
        elif mode == 'main_window':
            self.game = MainWindow(settings)
        elif mode == 'settings':
            self.game = SettingsWindow(settings)

    def game_cycle(self) -> None:
        self.game.game_cycle()


def get_game(mode):
    return Game(Settings(SETTINGS_FILE).settings, mode)


def run(game):
    start_mode = game.game.mode
    game.game_cycle()
    if game.game.mode != start_mode:
        new_mode = game.game.mode
        game = get_game(new_mode)
        start_mode = new_mode
        run(game)

game = get_game('main_window')
run(game)
pygame.quit()
