import re
from datetime import datetime, timedelta

from module.base.decorator import Config
from module.base.filter import Filter
from module.base.utils import *
from module.commission.project_data import *
from module.logger import logger
from module.ocr.ocr import Ocr, Duration
from module.reward.assets import *

COMMISSION_FILTER = Filter(
    regex=re.compile(
        '(major|daily|extra|urgent|night)?'
        '-?'
        '(resource|chip|event|drill|part|cube|oil|book|retrofit|box|gem|ship)?'
        '-?'
        '(\d\d?:\d\d)?'
        '(\d\d?.\d\d?|\d\d?)?'
    ),
    attr=('category_str', 'genre_str', 'duration_hm', 'duration_hour'),
    preset=('shortest')
)
SHORTEST_FILTER = """
0:30
> 1 > 1:10 > 1:20 > 1:30 > 1:40 > 1:45
> 2 > 2:15 > 2:30 > 2:40
> 3 > 3:20
> 4 > 5 > 5:20
> 6 > 7 > 8 > 9 > 10 > 12
"""


class SuffixOcr(Ocr):
    def pre_process(self, image):
        image = super().pre_process(image)

        left = np.where(np.min(image[5:-5, :], axis=0) < 85)[0]
        if len(left):
            image = image[:, left[-1] - 15:]

        return image


class Commission:
    button: Button
    name: str
    suffix: str
    genre: str
    status: str
    duration: timedelta
    expire: timedelta

    def __init__(self, image, y, config):
        self.config = config
        self.y = y
        self.area = (188, y - 119, 1199, y)
        self.image = image
        self.valid = True
        self.commission_parse()

        if not self.duration.total_seconds():
            self.valid = False

        self.create_time = datetime.now()
        self.category_str = 'unknown'
        self.genre_str = 'unknown'
        self.duration_hour = 'unknown'
        self.duration_hm = 'unknown'
        if self.valid:
            self.category_str, self.genre_str = self.genre.split('_', 1)
            self.duration_hour = str(int(self.duration.total_seconds() / 36) / 100).strip('.0')
            self.duration_hm = str(self.duration).rsplit(':', 1)[0]

    @Config.when(SERVER='en')
    def commission_parse(self):
        # Name
        # This is different from CN, EN has longer names
        area = area_offset((176, 23, 420, 53), self.area[0:2])
        button = Button(area=area, color=(), button=area, name='COMMISSION')
        ocr = Ocr(button, lang='cnocr')
        self.button = button
        self.name = ocr.ocr(self.image)
        self.genre = self.commission_name_parse(self.name.upper())

        # Suffix
        ocr = SuffixOcr(button, lang='azur_lane', letter=(255, 255, 255), threshold=128, alphabet='IV')
        self.suffix = self.beautify_name(ocr.ocr(self.image))

        # Duration time
        area = area_offset((290, 68, 390, 95), self.area[0:2])
        button = Button(area=area, color=(), button=area, name='DURATION')
        ocr = Duration(button)
        self.duration = ocr.ocr(self.image)

        # Expire time
        area = area_offset((-49, 68, -45, 84), self.area[0:2])
        button = Button(area=area, color=(189, 65, 66),
                        button=area, name='IS_URGENT')
        if button.appear_on(self.image):
            area = area_offset((-49, 67, 45, 94), self.area[0:2])
            button = Button(area=area, color=(), button=area, name='EXPIRE')
            ocr = Duration(button)
            self.expire = ocr.ocr(self.image)
        else:
            self.expire = timedelta(seconds=0)

        # Status
        area = area_offset((179, 71, 187, 93), self.area[0:2])
        dic = {
            0: 'finished',
            1: 'running',
            2: 'pending'
        }
        color = get_color(self.image, area)
        if self.genre == 'event_daily':
            color -= [50, 30, 20]
        self.status = dic[int(np.argmax(color))]

    @Config.when(SERVER='jp')
    def commission_parse(self):
        # Name
        area = area_offset((176, 23, 420, 53), self.area[0:2])
        button = Button(area=area, color=(), button=area, name='COMMISSION')
        ocr = Ocr(button, lang='jp')
        self.button = button
        self.name = ocr.ocr(self.image)
        self.genre = self.commission_name_parse(self.name)

        # Suffix
        ocr = SuffixOcr(button, lang='azur_lane', letter=(255, 255, 255), threshold=128, alphabet='IV')
        self.suffix = self.beautify_name(ocr.ocr(self.image))

        # Duration time
        area = area_offset((290, 68, 390, 95), self.area[0:2])
        button = Button(area=area, color=(), button=area, name='DURATION')
        ocr = Duration(button)
        self.duration = ocr.ocr(self.image)

        # Expire time
        area = area_offset((-49, 68, -45, 84), self.area[0:2])
        button = Button(area=area, color=(189, 65, 66),
                        button=area, name='IS_URGENT')
        if button.appear_on(self.image):
            area = area_offset((-49, 67, 45, 94), self.area[0:2])
            button = Button(area=area, color=(), button=area, name='EXPIRE')
            ocr = Duration(button)
            self.expire = ocr.ocr(self.image)
        else:
            self.expire = timedelta(seconds=0)

        # Status
        area = area_offset((179, 71, 187, 93), self.area[0:2])
        dic = {
            0: 'finished',
            1: 'running',
            2: 'pending'
        }
        color = get_color(self.image, area)
        if self.genre == 'event_daily':
            color -= [50, 30, 20]
        self.status = dic[int(np.argmax(color))]

    @Config.when(SERVER='cn')
    def commission_parse(self):
        # Name
        area = area_offset((176, 23, 420, 53), self.area[0:2])
        button = Button(area=area, color=(), button=area, name='COMMISSION')
        ocr = Ocr(button, lang='cnocr', threshold=256)
        self.button = button
        self.name = ocr.ocr(self.image)
        self.genre = self.commission_name_parse(self.name)

        # Suffix
        ocr = SuffixOcr(button, lang='azur_lane', letter=(255, 255, 255), threshold=128, alphabet='IV')
        self.suffix = self.beautify_name(ocr.ocr(self.image))

        # Duration time
        area = area_offset((290, 68, 390, 95), self.area[0:2])
        button = Button(area=area, color=(), button=area, name='DURATION')
        ocr = Duration(button)
        self.duration = ocr.ocr(self.image)

        # Expire time
        area = area_offset((-49, 68, -45, 84), self.area[0:2])
        button = Button(area=area, color=(189, 65, 66),
                        button=area, name='IS_URGENT')
        if button.appear_on(self.image):
            area = area_offset((-49, 67, 45, 94), self.area[0:2])
            button = Button(area=area, color=(), button=area, name='EXPIRE')
            ocr = Duration(button)
            self.expire = ocr.ocr(self.image)
        else:
            self.expire = timedelta(seconds=0)

        # Status
        area = area_offset((179, 71, 187, 93), self.area[0:2])
        dic = {
            0: 'finished',
            1: 'running',
            2: 'pending'
        }
        color = get_color(self.image, area)
        if self.genre == 'event_daily':
            color -= [50, 30, 20]
        self.status = dic[int(np.argmax(color))]

    def __str__(self):
        if self.valid:
            if self.expire:
                return f'{self.name} | {self.suffix} ' \
                    f'(Genre: {self.genre}, Status: {self.status}, Duration: {self.duration}, Expire: {self.expire})'
            else:
                return f'{self.name} | {self.suffix} ' \
                    f'(Genre: {self.genre}, Status: {self.status}, Duration: {self.duration})'
        else:
            return f'{self.name} | {self.suffix} ' \
                f'(Invalid)'

    def __eq__(self, other):
        """
        Args:
            other (Commission):

        Returns:
            bool:
        """
        if not isinstance(other, Commission):
            return False
        threshold = timedelta(seconds=120)
        if not self.valid or not other.valid:
            return False
        if self.genre != other.genre or self.status != other.status:
            return False
        if self.category_str == 'daily':
            if self.suffix != other.suffix:
                return False
        if (other.duration < self.duration - threshold) or (other.duration > self.duration + threshold):
            return False
        if (not self.expire and other.expire) or (self.expire and not other.expire):
            return False
        if self.expire and other.expire:
            if (other.expire < self.expire - threshold) or (other.expire > self.expire + threshold):
                return False

        return True

    def __hash__(self):
        return hash(f'{self.genre}_{self.name}')

    def parse_time(self, string):
        """
        Args:
            string (str): Such as 01:00:00, 05:47:10, 17:50:51.

        Returns:
            timedelta: datetime.timedelta instance.
        """
        string = string.replace('D', '0')  # Poor OCR
        result = re.search('(\d+):(\d+):(\d+)', string)
        if not result:
            logger.warning(f'Invalid time string: {string}')
            self.valid = False
            return None
        else:
            result = [int(s) for s in result.groups()]
            return timedelta(hours=result[0], minutes=result[1], seconds=result[2])

    @Config.when(SERVER='en')
    def commission_name_parse(self, string):
        """
        Args:
            string (str): Commission name, such as 'NYB要员护卫'.

        Returns:
            str: Commission genre, such as 'urgent_gem'.
        """
        # string = string.replace(' ', '').replace('-', '')
        if self.is_event_commission():
            return 'daily_event'
        for key, value in dictionary_en.items():
            for keyword in value:
                if keyword in string:
                    return key

        logger.warning(f'Name with unknown genre: {string}')
        self.valid = False
        return ''

    @Config.when(SERVER='jp')
    def commission_name_parse(self, string):
        """
        Args:
            string (str): Commission name, such as 'NYB要员护卫'.

        Returns:
            str: Commission genre, such as 'urgent_gem'.
        """
        if self.is_event_commission():
            return 'daily_event'
        import jellyfish
        min_key = ''
        min_distance = 100
        string = re.sub(r'[\x00-\x7F]', '', string)
        for key, value in dictionary_jp.items():
            for keyword in value:
                distance = jellyfish.levenshtein_distance(keyword, string)
                if distance < min_distance:
                    min_key = key
                    min_distance = distance
        if min_distance < 3:
            return min_key

        logger.warning(f'Name with unknown genre: {string}')
        self.valid = False
        return ''

    @Config.when(SERVER=None)
    def commission_name_parse(self, string):
        """
        Args:
            string (str): Commission name, such as 'NYB要员护卫'.

        Returns:
            str: Commission genre, such as 'urgent_gem'.
        """
        if self.is_event_commission():
            return 'daily_event'
        for key, value in dictionary_cn.items():
            for keyword in value:
                if keyword in string:
                    return key

        logger.warning(f'Name with unknown genre: {string}')
        self.valid = False
        return ''

    def is_event_commission(self):
        """
        Returns:
            bool:
        """
        # Event commission in Vacation Lane, with pink area on the left.
        # area = area_offset((5, 5, 30, 30), self.area[0:2])
        # return color_similar(color1=get_color(self.image, area), color2=(239, 166, 231))

        # 2021.07.22 Event commissions in The Idol Master event, with
        # area = area_offset((5, 5, 30, 30), self.area[0:2])
        # return color_similar(color1=get_color(self.image, area), color2=(235, 173, 161))

        return False

    def convert_to_night(self):
        if self.valid and self.category_str == 'extra':
            self.category_str = 'night'
            self.genre = f'{self.category_str}_{self.genre_str}'

    def convert_to_running(self):
        if self.valid:
            self.status = 'running'
            self.create_time = datetime.now()

    @property
    def finish_time(self):
        if self.valid and self.status == 'running':
            return (self.create_time + self.duration).replace(microsecond=0)
        else:
            return None

    @staticmethod
    def beautify_name(name):
        name = name.strip()
        name = re.sub(r'VI$', 'Ⅵ', name)
        name = re.sub(r'IV$', 'Ⅳ', name)
        name = re.sub(r'V$', 'Ⅴ', name)
        name = re.sub(r'III$', 'Ⅲ', name)
        name = re.sub(r'II$', 'Ⅱ', name)
        name = re.sub(r'I$', 'Ⅰ', name)
        return name