import curses
import math
import os
import traceback
import threading
import time
import random
import getpass
import json
import sqlite3
import string
import re
import completer
import datetime

class CursedMenu(object):
    #TODO: name your plant
    '''A class which abstracts the horrors of building a curses-based menu system'''
    def __init__(self, this_plant, this_data):
        '''Initialization'''
        self.initialized = False
        self.screen = curses.initscr()
        curses.noecho()
        curses.raw()
        if curses.has_colors():
            curses.start_color()
        try:
            curses.curs_set(0)
        except curses.error:
            # Not all terminals support this functionality.
            # When the error is ignored the screen will look a little uglier, but that's not terrible
            # So in order to keep botany as accesible as possible to everyone, it should be safe to ignore the error.
            pass
        self.screen.keypad(1)
        self.plant = this_plant
        self.visited_plant = None
        self.user_data = this_data
        self.plant_string = self.plant.parse_plant()
        self.plant_ticks = str(int(self.plant.ticks))
        self.exit = False
        self.infotoggle = 0
        self.maxy, self.maxx = self.screen.getmaxyx()
        # Highlighted and Normal line definitions
        if curses.has_colors():
            self.define_colors()
            self.highlighted = curses.color_pair(1)
        else:
            self.highlighted = curses.A_REVERSE
        self.normal = curses.A_NORMAL
        # Threaded screen update for live changes
        screen_thread = threading.Thread(target=self.update_plant_live, args=())
        screen_thread.daemon = True
        screen_thread.start()
        # Recusive lock to prevent both threads from drawing at the same time
        self.screen_lock = threading.RLock()
        self.screen.clear()
        self.show(["вода","осмотреть","сад","посетить", "инструкция"], title=' botany rus by PAHEN', subtitle='варианты')

    def define_colors(self):
        # TODO: implement colors
        # set curses color pairs manually
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(7, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(8, curses.COLOR_CYAN, curses.COLOR_BLACK)

    def show(self, options, title, subtitle):
        # Draws a menu with parameters
        self.set_options(options)
        self.update_options()
        self.title = title
        self.subtitle = subtitle
        self.selected = 0
        self.initialized = True
        self.draw_menu()

    def update_options(self):
        # Makes sure you can get a new plant if it dies
        if self.plant.dead or self.plant.stage == 5:
            if "harvest" not in self.options:
                self.options.insert(-1,"harvest")
        else:
            if "harvest" in self.options:
                self.options.remove("harvest")

    def set_options(self, options):
        # Validates that the last option is "exit"
        if options[-1] != 'exit':
            options.append('exit')
        self.options = options

    def draw(self):
        # Draw the menu and lines
        self.maxy, self.maxx = self.screen.getmaxyx()
        self.screen_lock.acquire()
        self.screen.refresh()
        try:
            self.draw_default()
            self.screen.refresh()
        except Exception as exception:
            # Makes sure data is saved in event of a crash due to window resizing
            self.screen.clear()
            self.screen.addstr(0, 0, "Увеличить терминал!", curses.A_NORMAL)
            self.screen.refresh()
            self.__exit__()
            traceback.print_exc()
        self.screen_lock.release()

    def draw_menu(self):
        # Actually draws the menu and handles branching
        request = ""
        try:
            while request != "exit":
                self.draw()
                request = self.get_user_input()
                self.handle_request(request)
            self.__exit__()

        # Also calls __exit__, but adds traceback after
        except Exception as exception:
            self.screen.clear()
            self.screen.addstr(0, 0, "Увеличить терминал!", curses.A_NORMAL)
            self.screen.refresh()
            self.__exit__()
            #traceback.print_exc()
        except IOError as exception:
            self.screen.clear()
            self.screen.refresh()
            self.__exit__()

    def ascii_render(self, filename, ypos, xpos):
        # Prints ASCII art from file at given coordinates
        this_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),"art")
        this_filename = os.path.join(this_dir,filename)
        this_file = open(this_filename,"r")
        this_string = this_file.readlines()
        this_file.close()
        self.screen_lock.acquire()
        for y, line in enumerate(this_string, 2):
            self.screen.addstr(ypos+y, xpos, line, curses.A_NORMAL)
        # self.screen.refresh()
        self.screen_lock.release()

    def draw_plant_ascii(self, this_plant):
        ypos = 0
        xpos = int((self.maxx-37)/2 + 25)
        plant_art_list = [
            'poppy',
            'cactus',
            'aloe',
            'flytrap',
            'jadeplant',
            'fern',
            'daffodil',
            'sunflower',
            'baobab',
            'lithops',
            'hemp',
            'pansy',
            'iris',
            'agave',
            'ficus',
            'moss',
            'sage',
            'snapdragon',
            'columbine',
            'brugmansia',
            'palm',
            'pachypodium',
        ]
        if this_plant.dead == True:
            self.ascii_render('rip.txt', ypos, xpos)
        elif datetime.date.today().month == 10 and datetime.date.today().day == 31:
            self.ascii_render('jackolantern.txt', ypos, xpos)
        elif this_plant.stage == 0:
            self.ascii_render('seed.txt', ypos, xpos)
        elif this_plant.stage == 1:
            self.ascii_render('seedling.txt', ypos, xpos)
        elif this_plant.stage == 2:
            this_filename = plant_art_list[this_plant.species]+'1.txt'
            self.ascii_render(this_filename, ypos, xpos)
        elif this_plant.stage == 3 or this_plant.stage == 5:
            this_filename = plant_art_list[this_plant.species]+'2.txt'
            self.ascii_render(this_filename, ypos, xpos)
        elif this_plant.stage == 4:
            this_filename = plant_art_list[this_plant.species]+'3.txt'
            self.ascii_render(this_filename, ypos, xpos)

    def draw_default(self):
        # draws default menu
        clear_bar = " " * (int(self.maxx*2/3))
        self.screen_lock.acquire()
        self.screen.addstr(1, 2, self.title, curses.A_STANDOUT) # Title for this menu
        self.screen.addstr(3, 2, self.subtitle, curses.A_BOLD) #Subtitle for this menu
        # clear menu on screen
        for index in range(len(self.options)+1):
            self.screen.addstr(4+index, 4, clear_bar, curses.A_NORMAL)
        # display all the menu items, showing the 'pos' item highlighted
        for index in range(len(self.options)):
            textstyle = self.normal
            if index == self.selected:
                textstyle = self.highlighted
            self.screen.addstr(4+index ,4, clear_bar, curses.A_NORMAL)
            self.screen.addstr(4+index ,4, "%d - %s" % (index+1, self.options[index]), textstyle)

        self.screen.addstr(12, 2, clear_bar, curses.A_NORMAL)
        self.screen.addstr(13, 2, clear_bar, curses.A_NORMAL)
        self.screen.addstr(12, 2, "plant: ", curses.A_DIM)
        self.screen.addstr(12, 9, self.plant_string, curses.A_NORMAL)
        self.screen.addstr(13, 2, "score: ", curses.A_DIM)
        self.screen.addstr(13, 9, self.plant_ticks, curses.A_NORMAL)

        # display fancy water gauge
        if not self.plant.dead:
            water_gauge_str = self.water_gauge()
            self.screen.addstr(4,14, water_gauge_str, curses.A_NORMAL)
        else:
            self.screen.addstr(4,13, clear_bar, curses.A_NORMAL)
            self.screen.addstr(4,14, "(   RIP   )", curses.A_NORMAL)

        # draw cute ascii from files
        if self.visited_plant:
            # Needed to prevent drawing over a visited plant
            self.draw_plant_ascii(self.visited_plant)
        else:
            self.draw_plant_ascii(self.plant)
        self.screen_lock.release()

    def water_gauge(self):
        # build nice looking water gauge
        water_left_pct = 1 - ((time.time() - self.plant.watered_timestamp)/86400)
        # don't allow negative value
        water_left_pct = max(0, water_left_pct)
        water_left = int(math.ceil(water_left_pct * 10))
        water_string = "(" + (")" * water_left) + ("." * (10 - water_left)) + ") " + str(int(water_left_pct * 100)) + "% "
        return water_string

    def update_plant_live(self):
        # updates plant data on menu screen, live!
        while not self.exit:
            self.plant_string = self.plant.parse_plant()
            self.plant_ticks = str(int(self.plant.ticks))
            if self.initialized:
                self.update_options()
                self.draw()
            time.sleep(1)

    def get_user_input(self):
        # gets the user's input
        try:
            user_in = self.screen.getch() # Gets user input
        except Exception as e:
            self.__exit__()
        if user_in == -1: # Input comes from pipe/file and is closed
            raise IOError
        ## DEBUG KEYS - enable these lines to see curses key codes
        # self.screen.addstr(2, 2, str(user_in), curses.A_NORMAL)
        # self.screen.refresh()

        # Resize sends curses.KEY_RESIZE, update display
        if user_in == curses.KEY_RESIZE:
            self.maxy,self.maxx = self.screen.getmaxyx()
            self.screen.clear()
            self.screen.refresh()

        # enter, exit, and Q Keys are special cases
        if user_in == 10:
            return self.options[self.selected]
        if user_in == 27:
            return self.options[-1]
        if user_in == 113:
            self.selected = len(self.options) - 1
            return

        # this is a number; check to see if we can set it
        if user_in >= ord('1') and user_in <= ord(str(min(7,len(self.options)))):
            self.selected = user_in - ord('0') - 1 # convert keypress back to a number, then subtract 1 to get index
            return

        # increment or Decrement
        down_keys = [curses.KEY_DOWN, 14, ord('j')]
        up_keys = [curses.KEY_UP, 16, ord('k')]

        if user_in in down_keys: # down arrow
            self.selected += 1
        if user_in in up_keys: # up arrow
            self.selected -=1

        # modulo to wrap menu cursor
        self.selected = self.selected % len(self.options)
        return

    def format_garden_data(self,this_garden):
        # Returns list of lists (pages) of garden entries
        plant_table = []
        for plant_id in this_garden:
            if this_garden[plant_id]:
                if not this_garden[plant_id]["dead"]:
                    this_plant = this_garden[plant_id]
                    plant_table.append((this_plant["owner"],
                                        this_plant["age"],
                                        int(this_plant["score"]),
                                        this_plant["description"]))
        return plant_table

    def format_garden_entry(self, entry):
        return "{:14.14} - {:>16} - {:>8}p - {}".format(*entry)

    def sort_garden_table(self, table, column, ascending):
        """ Sort table in place by a specified column """
        def key(entry):
            entry = entry[column]
            # In when sorting ages, convert to seconds
            if column == 1:
                coeffs = [24*60*60, 60*60, 60, 1]
                nums = [int(n[:-1]) for n in entry.split(":")]
                if len(nums) == len(coeffs):
                    entry = sum(nums[i] * coeffs[i] for i in range(len(nums)))
            return entry

        return table.sort(key=key, reverse=not ascending)

    def filter_garden_table(self, table, pattern):
        """ Filter table using a pattern, and return the new table """
        def filterfunc(entry):
            if len(pattern) == 0:
                return True
            entry_txt = self.format_garden_entry(entry)
            try:
                result = bool(re.search(pattern, entry_txt))
            except Exception as e:
                # In case of invalid regex, don't match anything
                result = False
            return result
        return list(filter(filterfunc, table))

    def draw_garden(self):
        # draws community garden
        # load data from sqlite db
        this_garden = self.user_data.retrieve_garden_from_db()
        # format data
        self.clear_info_pane()

        if self.infotoggle == 2:
            # the screen IS currently showing the garden (1 page), make the
            # text a bunch of blanks to clear it out
            self.infotoggle = 0
            return

        # if infotoggle isn't 2, the screen currently displays other stuff
        plant_table_orig = self.format_garden_data(this_garden)
        self.infotoggle = 2

        # print garden information OR clear it
        index = 0
        sort_column, sort_ascending = 0, True
        sort_keys = ["n", "a", "s", "d"] # Name, Age, Score, Description
        plant_table = plant_table_orig
        self.sort_garden_table(plant_table, sort_column, sort_ascending)
        while True:
            entries_per_page = self.maxy - 16
            index_max = min(len(plant_table), index + entries_per_page)
            plants = plant_table[index:index_max]
            page = [self.format_garden_entry(entry) for entry in plants]
            self.screen_lock.acquire()
            self.draw_info_text(page)
            # Multiple pages, paginate and require keypress
            page_text = "(%d-%d/%d) | sp/далее | bksp/предыдущий | s <col #>/сортировка | f/филтер | q/выход" % (index, index_max, len(plant_table))
            self.screen.addstr(self.maxy-2, 2, page_text)
            self.screen.refresh()
            self.screen_lock.release()
            c = self.screen.getch()
            if c == -1: # Input comes from pipe/file and is closed
                raise IOError
            self.infotoggle = 0

            # Quit
            if c == ord("q") or c == ord("x") or c == 27:
                break
            # Next page
            elif c in [curses.KEY_ENTER, curses.KEY_NPAGE, ord(" "), ord("\n")]:
                index += entries_per_page
                if index >= len(plant_table):
                    break
            # Previous page
            elif c == curses.KEY_BACKSPACE or c == curses.KEY_PPAGE:
                index = max(index - entries_per_page, 0)
            # Next line
            elif c == ord("j") or c == curses.KEY_DOWN:
                index = max(min(index + 1, len(plant_table) - 1), 0)
            # Previous line
            elif c == ord("k") or c == curses.KEY_UP:
                index = max(index - 1, 0)
            # Sort entries
            elif c == ord("s"):
                c = self.screen.getch()
                if c == -1: # Input comes from pipe/file and is closed
                    raise IOError
                column = -1
                if c < 255 and chr(c) in sort_keys:
                    column = sort_keys.index(chr(c))
                elif ord("1") <= c <= ord("4"):
                    column = c - ord("1")
                if column != -1:
                    if sort_column == column:
                        sort_ascending = not sort_ascending
                    else:
                        sort_column = column
                        sort_ascending = True
                    self.sort_garden_table(plant_table, sort_column, sort_ascending)
            # Filter entries
            elif c == ord("/") or c == ord("f"):
                self.screen.addstr(self.maxy-2, 2, "Filter: " + " " * (len(page_text)-8))
                pattern = self.get_user_string(10, self.maxy-2, lambda x: x in string.printable)
                plant_table = self.filter_garden_table(plant_table_orig, pattern)
                self.sort_garden_table(plant_table, sort_column, sort_ascending)
                index = 0

            # Clear page before drawing next
            self.clear_info_pane()
        self.clear_info_pane()

    def get_plant_description(self, this_plant):
        output_text = ""
        this_species = this_plant.species_list[this_plant.species]
        this_color = this_plant.color_list[this_plant.color]
        this_stage = this_plant.stage

        stage_descriptions = {
                0:[
            "Вы рады своему новому семени.",
            "Вам интересно, в какое растение вырастет ваше семя.",
            "Вы готовы к новому началу с этим растением.",
            "Вы устали ждать, пока ваше семя вырастет.",
            "Вы хотели бы, чтобы ваше семя сказало вам, что ему нужно.",
            "Вы чувствуете дух внутри своего семени.",
            "Эти крендельки вызывают жажду.",
            "Молодец, Энн!",
            "Видеть в семени то, что в нем есть, - это гениально - Лао Цзы",
            ],
                1:[
            "Саженец наполняет вас надеждой.",
            "Саженец колышется на ветру.",
            "Вы можете различить крошечный листок - или это колючка?",
            "Вы чувствуете, как росток смотрит на вас.",
            "Вы целуете свой росток.",
            "Вы думаете обо всех росточках, которые были до него.",
            "Вы и ваш росток - отличная команда.",
            "Ваш росток растет медленно и спокойно.",
            "Вы размышляете о путях, по которым может пойти жизнь вашего растения.",
            ],
                2:[
            " " + this_species + " заставляет вас чувствовать себя расслабленным.",
            "Ты поешь песню своему " + this_species + ".",
            "Вы тихо сидите со своими " + this_species + " в течение нескольких минут.",
            "Ваш " + this_species + " выглядит довольно хорошо.",
            "Ты играешь громкое техно для своих " + this_species + ".",
            "Ты играешь на пианино для своего " + this_species + ".",
            "Ты читаешь рэп для своих " + this_species + ".",
            "Ты насвистываешь мелодию для своего " + this_species + ".",
            "Вы читаете стихотворение своему " + this_species + ".",
            "Вы раскрываете секрет своему " + this_species + ".",
            "Вы ставите свою любимую пластинку для своего " + this_species + ".",
            ],
                3:[
            "Ваш " + this_species + " отлично растет!",
            "YВы гордитесь самоотверженностью, которая потребовалась для развития вашего " + this_species + ".",
            "Вы делаете глубокий вдох с " + this_species + ".",
            "Вы думаете обо всех словах, которые рифмуются с " + this_species + ".",
            " " + this_species + " выглядит полным жизни.",
            " " + this_species + " вдохновляет вас.",
            "Ваш " + this_species + " заставляет забыть о своих проблемах.",
            "Ваш " + this_species + " дает вам повод продолжать.",
            "Смотря на свой " + this_species + " помогает сосредоточиться на главном.",
            "Ты думаешь о том, как хорошо " + this_species + " выглядит здесь.",
            "Бутоны твоих " + this_species + " может скоро зацвести.",
            ],
                4:[
            " " + this_color + " цветы хорошо смотрятся на вашем " + this_species +"!",
            " " + this_color + " цветы распустились и наполняют вас позитивом.",
            " " + this_color + " цветы напоминают вам о детстве.",
            " " + this_color + " цветы напоминают вам о весеннем утре.",
            " " + this_color + " цветы напоминают о забытом воспоминании.",
            " " + this_color + " цветы напоминают вам о вашем счастливом месте.",
            "Аромат " + this_color + " цветы заряжают вас энергией.",
            " " + this_species + " выросла красивой " + this_color + " цветы.",
            " " + this_color + " лепестки напоминают вам о любимой футболке, которую вы потеряли.",
            " " + this_color + " цветы напоминают вам о вашей влюбленности.",
            "Вы чувствуете запах " + this_color + " цветы и наполнены миром.",
            ],
                5:[
            "Вы с нежностью вспоминаете время, проведенное в заботе о своем " + this_species + ".",
            "Стручки семян выросли на вашем " + this_species + ".",
            "Вы чувствуете, что ваш " + this_species + " ценит вашу заботу.",
            " " + this_species + " наполняет тебя любовью.",
            "Вы готовы ко всему, что придет после вашего " + this_species + ".",
            "Вам не терпится начать выращивать свое следующее растение.",
            "Вы размышляете о том, когда ваш " + this_species + " был всего лишь ростком.",
            "Вы ностальгируете по ранним дням, проведенным с вашим " + this_species + ".",
            ],
                99:[
            "Вы хотели бы лучше заботиться о своем растении.",
            "Если бы вы чаще поливали свое растение...",
            "Ваше растение погибло, но всегда можно поробовать еще раз.",
            "Вы плачете над увядшими листьями вашего растения.",
            "Ваше растение умерло. Возможно, вам нужно начать все сначала.",
            ],
        }
        # self.life_stages is tuple containing length of each stage
        # (seed, seedling, young, mature, flowering)
        if this_plant.dead:
            this_stage = 99

        this_stage_descriptions = stage_descriptions[this_stage]
        description_num = random.randint(0,len(this_stage_descriptions) - 1)
        # If not fully grown
        if this_stage <= 4:
            # Growth hint
            if this_stage >= 1:
                last_growth_at = this_plant.life_stages[this_stage - 1]
            else:
                last_growth_at = 0
            ticks_since_last = this_plant.ticks - last_growth_at
            ticks_between_stage = this_plant.life_stages[this_stage] - last_growth_at
            if ticks_since_last >= ticks_between_stage * 0.8:
                output_text += "Вы заметили, что ваше растение выглядит иначе.\n"

        output_text += this_stage_descriptions[description_num] + "\n"

        # if seedling
        if this_stage == 1:
            species_options = [this_plant.species_list[this_plant.species],
                    this_plant.species_list[(this_plant.species+3) % len(this_plant.species_list)],
                    this_plant.species_list[(this_plant.species-3) % len(this_plant.species_list)]]
            random.shuffle(species_options)
            plant_hint = "Это может быть a(n) " + species_options[0] + ", " + species_options[1] + ", or " + species_options[2]
            output_text += plant_hint + ".\n"

        # if young plant
        if this_stage == 2:
            if this_plant.rarity >= 2:
                rarity_hint = "Вы чувствуете, что ваше растение особенное."
                output_text += rarity_hint + ".\n"

        # if mature plant
        if this_stage == 3:
            color_options = [this_plant.color_list[this_plant.color],
                    this_plant.color_list[(this_plant.color+3) % len(this_plant.color_list)],
                    this_plant.color_list[(this_plant.color-3) % len(this_plant.color_list)]]
            random.shuffle(color_options)
            plant_hint = "Вы можете увидеть первые намеки на " + color_options[0] + ", " + color_options[1] + ", или " + color_options[2]
            output_text += plant_hint + ".\n"

        return output_text

    def draw_plant_description(self, this_plant):
        # If menu is currently showing something other than the description
        self.clear_info_pane()
        if self.infotoggle != 1:
            # get plant description before printing
            output_string = self.get_plant_description(this_plant)
            growth_multiplier = 1 + (0.2 * (this_plant.generation-1))
            output_string += "Поколение: {}\nТемп роста: {}x".format(self.plant.generation, growth_multiplier)
            self.draw_info_text(output_string)
            self.infotoggle = 1
        else:
            # otherwise just set toggle
            self.infotoggle = 0

    def draw_instructions(self):
        # Draw instructions on screen
        self.clear_info_pane()
        if self.infotoggle != 4:
            instructions_txt = ("Добро пожаловать в Botany. Вам дали семя.\n"
                                "из которого вырастет прекрасное растение. проверьте\n"
                                "в и поливайте ваше растение каждые 24 часа, чтобы оно\n"
                                "росло. 5 дней без воды = смерть. Ваше\n"
                                "астение зависит от вас и ваших друзей, чтобы жить!\n"
                                "больше информации можно найти в readme  :)\n"
                                "https://github.com/jifunks/botany/blob/master/README.md\n"
                                "                               cheers,\n"
                                "                               curio\n"
                                )
            self.draw_info_text(instructions_txt)
            self.infotoggle = 4
        else:
            self.infotoggle = 0

    def clear_info_pane(self):
        # Clears bottom part of screen
        self.screen_lock.acquire()
        clear_bar = " " * (self.maxx - 3)
        this_y = 14
        while this_y < self.maxy:
            self.screen.addstr(this_y, 2, clear_bar, curses.A_NORMAL)
            this_y += 1
        self.screen.refresh()
        self.screen_lock.release()

    def draw_info_text(self, info_text, y_offset = 0):
        # print lines of text to info pane at bottom of screen
        self.screen_lock.acquire()
        if type(info_text) is str:
            info_text = info_text.splitlines()
        for y, line in enumerate(info_text, 2):
            this_y = y+12 + y_offset
            if len(line) > self.maxx - 3:
                line = line[:self.maxx-3]
            if this_y < self.maxy:
                self.screen.addstr(this_y, 2, line, curses.A_NORMAL)
        self.screen.refresh()
        self.screen_lock.release()

    def harvest_confirmation(self):
        self.clear_info_pane()
        # get plant description before printing
        max_stage = len(self.plant.stage_list) - 1
        harvest_text = ""
        if not self.plant.dead:
            if self.plant.stage == max_stage:
                harvest_text += "Поздравляем! Вы вырастили свое растение до последней стадии роста.\n"
                harvest_text += "Ваше следующее растение будет расти со скоростью: {}x\n".format(1 + (0.2 * self.plant.generation))
        harvest_text += "Если вы соберете свое растение, то начнете все с семени.\nПродолжить? (Y/n)"
        self.draw_info_text(harvest_text)
        try:
            user_in = self.screen.getch() # Gets user input
        except Exception as e:
            self.__exit__()
        if user_in == -1: # Input comes from pipe/file and is closed
            raise IOError

        if user_in in [ord('Y'), ord('y')]:
            self.plant.start_over()
        else:
            pass
        self.clear_info_pane()

    def build_weekly_visitor_output(self, visitors):
        visitor_block = ""
        visitor_line = ""
        for visitor in visitors:
            this_visitor_string = str(visitor) + "({}) ".format(visitors[str(visitor)])
            if len(visitor_line + this_visitor_string) > self.maxx-3:
                visitor_block += '\n'
                visitor_line = ""
            visitor_block += this_visitor_string
            visitor_line += this_visitor_string
        return visitor_block

    def build_latest_visitor_output(self, visitors):
        visitor_line = ""
        for visitor in visitors:
            if len(visitor_line + visitor) > self.maxx-10:
                visitor_line += "and more"
                break
            visitor_line += visitor + ' '
        return [visitor_line]

    def get_weekly_visitors(self):
        game_dir = os.path.dirname(os.path.realpath(__file__))
        garden_db_path = os.path.join(game_dir, 'sqlite/garden_db.sqlite')
        conn = sqlite3.connect(garden_db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM visitors WHERE garden_name = '{}' ORDER BY weekly_visits".format(self.plant.owner))
        visitor_data = c.fetchall()
        conn.close()
        visitor_block = ""
        visitor_line = ""
        if visitor_data:
            for visitor in visitor_data:
                visitor_name = visitor[2]
                weekly_visits = visitor[3]
                this_visitor_string = "{}({}) ".format(visitor_name, weekly_visits)
                if len(visitor_line + this_visitor_string) > self.maxx-3:
                    visitor_block += '\n'
                    visitor_line = ""
                visitor_block += this_visitor_string
                visitor_line += this_visitor_string
        else:
            visitor_block = 'ниикто :('
        return visitor_block

    def get_user_string(self, xpos=3, ypos=15, filterfunc=str.isalnum, completer=None):
        # filter allowed characters using filterfunc, alphanumeric by default
        user_string = ""
        user_input = 0
        if completer:
            completer = completer(self)
        while user_input != 10:
            user_input = self.screen.getch()
            if user_input == -1: # Input comes from pipe/file and is closed
                raise IOError
            self.screen_lock.acquire()
            # osx and unix backspace chars...
            if user_input == 127 or user_input == 263:
                if len(user_string) > 0:
                    user_string = user_string[:-1]
                    if completer:
                        completer.update_input(user_string)
                    self.screen.addstr(ypos, xpos, " " * (self.maxx-xpos-1))
            elif user_input in [ord('\t'), curses.KEY_BTAB] and completer:
                direction = 1 if user_input == ord('\t') else -1
                user_string = completer.complete(direction)
                self.screen.addstr(ypos, xpos, " " * (self.maxx-xpos-1))
            elif user_input < 256 and user_input != 10:
                if filterfunc(chr(user_input)) or chr(user_input) == '_':
                    user_string += chr(user_input)
                    if completer:
                        completer.update_input(user_string)
            self.screen.addstr(ypos, xpos, str(user_string))
            self.screen.refresh()
            self.screen_lock.release()
        return user_string

    def visit_handler(self):
        self.clear_info_pane()
        self.draw_info_text("чей сад вы хотели бы посетить?")
        self.screen.addstr(15, 2, '~')
        if self.plant.visitors:
            latest_visitor_string = self.build_latest_visitor_output(self.plant.visitors)
            self.draw_info_text("с прошлого раза вас посетили: ", 3)
            self.draw_info_text(latest_visitor_string, 4)
            self.plant.visitors = []
        weekly_visitor_text = self.get_weekly_visitors()
        self.draw_info_text("на этой неделе вас посетили: ", 6)
        self.draw_info_text(weekly_visitor_text, 7)
        guest_garden = self.get_user_string(completer = completer.LoginCompleter)
        if not guest_garden:
            self.clear_info_pane()
            return None
        if guest_garden.lower() == getpass.getuser().lower():
            self.screen.addstr(16, 2, "вы уже здесь!")
            self.screen.getch()
            self.clear_info_pane()
            return None
        home_folder = os.path.dirname(os.path.expanduser("~"))
        guest_json = home_folder + "/{}/.botany/{}_plant_data.json".format(guest_garden, guest_garden)
        guest_plant_description = ""
        if os.path.isfile(guest_json):
            with open(guest_json) as f:
                visitor_data = json.load(f)
                guest_plant_description = visitor_data['description']
                self.visited_plant = self.get_visited_plant(visitor_data)
        guest_visitor_file = home_folder + "/{}/.botany/visitors.json".format(guest_garden, guest_garden)
        if os.path.isfile(guest_visitor_file):
            water_success = self.water_on_visit(guest_visitor_file)
            if water_success:
                self.screen.addstr(16, 2, "...you watered ~{}'s {}...".format(str(guest_garden), guest_plant_description))
                if self.visited_plant:
                    self.draw_plant_ascii(self.visited_plant)
            else:
                self.screen.addstr(16, 2, "{}'s garden is locked, but you can see in...".format(guest_garden))
        else:
            self.screen.addstr(16, 2, "i can't seem to find directions to {}...".format(guest_garden))
        try:
            self.screen.getch()
            self.clear_info_pane()
            self.draw_plant_ascii(self.plant)
        finally:
            self.visited_plant = None

    def water_on_visit(self, guest_visitor_file):
        visitor_data = {}
        # using -1 here so that old running instances can be watered
        guest_data = {'user': getpass.getuser(), 'timestamp': int(time.time()) - 1}
        if os.path.isfile(guest_visitor_file):
            if not os.access(guest_visitor_file, os.W_OK):
                return False
            with open(guest_visitor_file) as f:
                visitor_data = json.load(f)
            visitor_data.append(guest_data)
            with open(guest_visitor_file, mode='w') as f:
                f.write(json.dumps(visitor_data, indent=2))
            return True

    def get_visited_plant(self, visitor_data):
        """ Returns a drawable pseudo plant object from json data """
        class VisitedPlant: pass
        plant = VisitedPlant()
        plant.stage = 0
        plant.species = 0

        if "is_dead" not in visitor_data:
            return None
        plant.dead = visitor_data["is_dead"]
        if plant.dead:
            return plant

        if "stage" in visitor_data:
            stage = visitor_data["stage"]
            if stage in self.plant.stage_list:
                plant.stage = self.plant.stage_list.index(stage)

        if "species" in visitor_data:
            species = visitor_data["species"]
            if species in self.plant.species_list:
                plant.species = self.plant.species_list.index(species)
            else:
                return None
        elif plant.stage > 1:
            return None
        return plant

    def handle_request(self, request):
        # Menu options call functions here
        if request == None: return
        if request == "harvest":
            self.harvest_confirmation()
        if request == "вода":
            self.plant.water()
        if request == "осмотреть":
            try:
                self.draw_plant_description(self.plant)
            except Exception as exception:
                self.screen.refresh()
                # traceback.print_exc()
        if request == "инструкция":
            try:
                self.draw_instructions()
            except Exception as exception:
                self.screen.refresh()
                # traceback.print_exc()
        if request == "посетить":
            try:
                self.visit_handler()
            except Exception as exception:
                self.screen.refresh()
                # traceback.print_exc()
        if request == "сад":
            try:
                self.draw_garden()
            except Exception as exception:
                self.screen.refresh()
                # traceback.print_exc()

    def __exit__(self):
        self.exit = True
        cleanup()

def cleanup():
    try:
        curses.curs_set(2)
    except curses.error:
        # cursor not supported; just ignore
        pass
    curses.endwin()
    os.system('clear')

