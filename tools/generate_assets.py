"""Создаёт оригинальные спрайты и звуки. Запускать один раз, не из игрового цикла.

Использует только Pygame и стандартную библиотеку. Пути не зависят от cwd.
Готовые файлы уже включены в проект; генератор нужен для изучения и изменения.
"""
from pathlib import Path
import array
import math
import os
import random
import wave

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

ROOT = Path(__file__).resolve().parents[1] / "assets"
IMAGES = ROOT / "images"
AUDIO = ROOT / "audio"
SCALE = 3


class Canvas:
    """Рисуем в тройном размере, затем уменьшаем для сглаженных краёв."""
    def __init__(self, size):
        self.size = size
        self.surface = pygame.Surface((size[0] * SCALE, size[1] * SCALE), pygame.SRCALPHA)

    def points(self, points):
        return [(round(x*SCALE), round(y*SCALE)) for x, y in points]

    def polygon(self, color, points, width=0):
        pygame.draw.polygon(self.surface, color, self.points(points), round(width*SCALE))

    def line(self, color, a, b, width=1):
        pygame.draw.line(self.surface, color, self.points([a])[0], self.points([b])[0], max(1, round(width*SCALE)))

    def ellipse(self, color, rect, width=0):
        pygame.draw.ellipse(self.surface, color, tuple(round(v*SCALE) for v in rect), round(width*SCALE))

    def circle(self, color, center, radius, width=0):
        pygame.draw.circle(self.surface, color, self.points([center])[0], round(radius*SCALE), round(width*SCALE))

    def ship(self, points, hull=(30, 51, 72), edge=(69, 197, 226)):
        self.polygon((*edge, 35), points, 4)
        self.polygon(hull, points)
        self.polygon(edge, points, .8)

    def save(self, name, aliases=()):
        image = pygame.transform.smoothscale(self.surface, self.size)
        for filename in (name, *aliases):
            pygame.image.save(image, str(IMAGES / f"{filename}.png"))


def player():
    c = Canvas((58, 72))
    c.ship([(29,3),(39,34),(46,46),(54,55),(51,66),(36,60),(29,68),(22,60),(7,66),(4,55),(12,46),(19,34)])
    c.polygon((48,84,111), [(29,6),(24,24),(24,55),(29,63),(34,55),(34,24)])
    for flip in (-1,1):
        c.polygon((19,35,56), [(29+flip*10,33),(29+flip*23,55),(29+flip*20,61),(29+flip*9,53)])
        c.line((66,151,179), (29+flip*10,40), (29+flip*18,55), 1.2)
        c.line((90,223,238), (29+flip*20,55), (29+flip*20,61), 1.3)
        c.ellipse((26,102,180,65), (29+flip*11-5,56,10,15))
        c.ellipse((56,172,255), (29+flip*11-3,57,6,10))
        c.ellipse((180,247,255), (29+flip*11-1.4,58,2.8,6))
    c.polygon((12,37,61), [(29,17),(24,28),(25,40),(33,40),(34,28)])
    c.polygon((83,231,245), [(29,20),(26,29),(26,36),(32,36),(32,29)])
    c.line((205,251,255), (29,23), (29,33), 1)
    c.line((70,142,177), (26,45), (32,45), 1)
    c.save("ship_player", ("player",))


def scout():
    c = Canvas((46,42))
    c.ship([(23,39),(17,30),(5,17),(9,5),(18,11),(23,7),(28,11),(37,5),(41,17),(29,30)], (64,34,38), (230,101,70))
    c.polygon((104,48,48), [(23,10),(17,20),(23,34),(29,20)])
    c.polygon((255,165,93), [(20,15),(26,15),(23,26)])
    for x in (11,35):
        c.ellipse((247,92,37,55),(x-4,0,8,10))
        c.ellipse((255,126,70),(x-2,3,4,6))
    c.line((207,71,57),(10,16),(18,26),1)
    c.line((207,71,57),(36,16),(28,26),1)
    c.save("enemy_scout", ("scout",))


def gunner():
    c=Canvas((58,52))
    c.ship([(29,49),(18,39),(17,29),(6,33),(4,16),(14,8),(23,11),(29,4),(35,11),(44,8),(54,16),(52,33),(41,29),(40,39)],(66,37,42),(244,108,77))
    c.polygon((103,54,57),[(29,9),(22,18),(22,36),(29,44),(36,36),(36,18)])
    c.polygon((245,148,77),[(25,16),(33,16),(32,27),(26,27)])
    for x in (11,47):
        c.polygon((30,26,36),[(x-4,20),(x+4,20),(x+4,39),(x-4,39)])
        c.line((255,178,115),(x,24),(x,40),2)
        c.ellipse((255,107,50),(x-3,7,6,7))
    c.line((222,91,68),(24,34),(34,34),1)
    c.save("enemy_gunner",("gunner",))


def interceptor():
    c=Canvas((50,48))
    c.ship([(25,45),(19,27),(4,34),(5,16),(11,4),(18,15),(25,7),(32,15),(39,4),(45,16),(46,34),(31,27)],(61,28,49),(239,86,120))
    c.polygon((94,35,64),[(25,11),(20,19),(21,32),(25,41),(29,32),(30,19)])
    c.polygon((250,134,161),[(25,15),(22,21),(25,28),(28,21)])
    for flip in (-1,1):
        c.line((234,83,119),(25+flip*13,14),(25+flip*18,28),1.6)
        c.ellipse((255,70,122,65),(25+flip*12-4,0,8,12))
        c.ellipse((255,138,186),(25+flip*12-2,3,4,7))
    c.save("enemy_interceptor",("interceptor",))


def heavy():
    c=Canvas((78,62))
    c.ship([(39,59),(26,48),(14,51),(5,42),(4,17),(15,5),(28,9),(39,3),(50,9),(63,5),(74,17),(73,42),(64,51),(52,48)],(66,39,30),(239,151,66))
    c.polygon((104,61,37),[(39,8),(25,17),(25,41),(39,53),(53,41),(53,17)])
    c.polygon((146,78,39),[(39,12),(31,19),(31,38),(39,45),(47,38),(47,19)])
    c.polygon((255,177,87),[(33,18),(45,18),(43,27),(35,27)])
    for x in (13,21,57,65):
        c.line((37,24,26),(x,29),(x,52),5)
        c.line((222,97,44),(x,29),(x,50),2)
        c.ellipse((255,113,39),(x-2,9,4,8))
    c.line((221,138,68),(32,34),(46,34),1.5)
    c.line((221,138,68),(33,39),(45,39),1.5)
    c.save("enemy_heavy",("heavy",))


def boss():
    c=Canvas((248,154))
    outline=[(124,149),(98,118),(77,126),(62,114),(33,125),(9,104),(8,53),(26,21),(55,35),(77,23),(96,31),(124,8),(152,31),(171,23),(193,35),(222,21),(240,53),(239,104),(215,125),(186,114),(171,126),(150,118)]
    c.ship(outline,(52,30,41),(235,87,86))
    c.polygon((77,37,51),[(124,17),(90,43),(89,103),(124,137),(159,103),(158,43)])
    c.polygon((112,45,57),[(124,27),(102,48),(102,99),(124,122),(146,99),(146,48)])
    c.polygon((29,24,37),[(124,38),(110,51),(110,76),(124,87),(138,76),(138,51)])
    c.polygon((252,132,106),[(124,43),(115,54),(115,69),(124,77),(133,69),(133,54)])
    c.line((255,219,160),(124,50),(124,69),3)
    for flip in (-1,1):
        x=lambda v:124+flip*v
        c.polygon((70,40,48),[(x(41),39),(x(67),49),(x(94),36),(x(106),58),(x(104),96),(x(81),111),(x(52),98)])
        c.line((151,57,64),(x(53),54),(x(92),71),2)
        c.line((151,57,64),(x(54),64),(x(91),82),2)
        for d in (50,87):
            c.polygon((27,22,34),[(x(d-5),82),(x(d+5),82),(x(d+5),121),(x(d-5),121)])
            c.line((231,98,77),(x(d),88),(x(d),122),3)
            c.ellipse((251,102,74,60),(x(d)-6,118,12,10))
            c.ellipse((255,171,96),(x(d)-3,117,6,5))
        for d in (40,68,96):
            c.ellipse((242,97,45,40),(x(d)-7,17,14,20))
            c.ellipse((255,115,52),(x(d)-3,23,6,10))
    c.line((208,81,83),(112,99),(136,99),2)
    c.line((208,81,83),(117,107),(131,107),2)
    c.save("boss")


def meteor(name, size, seed):
    rng=random.Random(seed)
    c=Canvas((size,size))
    center=size/2
    radius=size*.43
    count=12 if size>40 else 9
    pts=[]
    for i in range(count):
        a=i*math.tau/count
        r=radius*rng.uniform(.82,1.04)
        pts.append((center+math.cos(a)*r,center+math.sin(a)*r))
    c.polygon((54,59,69),pts)
    c.polygon((122,125,130),pts, .8)
    for i in range(count):
        tone=70+int(32*(1-math.sin(i*math.tau/count)))
        c.polygon((tone,tone+3,tone+7),[pts[i],pts[(i+1)%count],(center+size*.02,center-size*.07)])
    # Кратеры с подсвеченным верхним краем и тёмной внутренней чашей.
    for _ in range(6 if size>40 else 3):
        angle=rng.uniform(0,math.tau)
        distance=rng.uniform(0,radius*.62)
        x=center+math.cos(angle)*distance
        y=center+math.sin(angle)*distance
        r=rng.uniform(size*.035,size*.11)
        c.circle((115,120,126),(x,y),r+size*.01)
        c.circle((53,58,68),(x,y+size*.015),r)
        c.circle((63,68,77),(x+r*.18,y+r*.25),r*.7)
    c.save(name)


def projectiles():
    for name,color in (("laser",(55,225,255)),("enemy_laser",(255,113,60))):
        c=Canvas((10,30))
        c.ellipse((*color,28),(0,0,10,30))
        c.ellipse((*color,70),(2,1,6,28))
        c.ellipse(color,(3.5,2,3,25))
        c.line((226,253,255),(5,4),(5,22),1)
        c.save(name)
    c=Canvas((16,34))
    c.ellipse((255,148,55,50),(0,18,16,16))
    c.polygon((255,166,59),[(8,33),(5,21),(11,21)])
    c.polygon((221,231,232),[(8,1),(12,8),(12,22),(4,22),(4,8)])
    c.polygon((61,192,218),[(8,2),(5,9),(11,9)])
    c.polygon((72,122,146),[(4,15),(1,25),(5,22),(11,22),(15,25),(12,15)])
    c.line((251,244,206),(8,25),(8,31),1)
    c.save("rocket")
    for name,color in (("plasma",(181,113,255)),("enemy_plasma",(255,81,143))):
        c=Canvas((24,30))
        c.ellipse((*color,25),(0,0,24,30))
        c.ellipse((*color,65),(3,3,18,24))
        c.ellipse(color,(6,6,12,17))
        c.ellipse((241,215,255),(9,8,6,11))
        c.ellipse((*color,180),(4,4,16,23),1)
        c.save(name)


def bonuses():
    for name,color in (("health",(76,227,177)),("credits",(245,199,87)),("shield",(85,185,252))):
        c=Canvas((32,32))
        pts=[(16,2),(28,9),(28,23),(16,30),(4,23),(4,9)]
        c.polygon((*color,40),pts,3)
        c.polygon((15,32,45),pts)
        c.polygon(color,pts,1)
        if name=="health":
            c.line(color,(10,16),(22,16),4)
            c.line(color,(16,10),(16,22),4)
        elif name=="credits":
            c.circle(color,(16,16),7,1.5)
            c.line(color,(16,11),(16,21),1.4)
            c.line(color,(12,14),(20,14),1.4)
            c.line(color,(12,18),(20,18),1.4)
        else:
            c.polygon(color,[(16,8),(23,11),(22,19),(16,25),(10,19),(9,11)],1.5)
            c.line(color,(13,16),(16,19),1.4)
            c.line(color,(16,19),(21,13),1.4)
        c.save(f"bonus_{name}")


def write_wav(name, duration, sample, rate=22050):
    values=array.array("h")
    for index in range(round(duration*rate)):
        value=max(-1.,min(1.,sample(index/rate)))
        values.append(round(value*32767))
    # WAV PCM имеет little endian независимо от архитектуры генератора.
    import sys
    if sys.byteorder!="little":
        values.byteswap()
    with wave.open(str(AUDIO/f"{name}.wav"),"wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(values.tobytes())


def audio():
    rng=random.Random(729)
    noise=[rng.uniform(-1,1) for _ in range(22050*2)]
    def n(t): return noise[int(t*22050)%len(noise)]
    def env(t,duration): return min(1,t/.006)*max(0,1-t/duration)**2
    write_wav("laser",.12,lambda t: .24*env(t,.12)*math.sin(math.tau*(1200*t-2600*t*t)))
    write_wav("rocket",.32,lambda t: .32*env(t,.32)*(.5*math.sin(math.tau*(140*t-130*t*t))+.5*n(t)))
    write_wav("plasma",.24,lambda t: .25*env(t,.24)*(math.sin(math.tau*(540*t-600*t*t))+.22*math.sin(math.tau*890*t)))
    write_wav("hit",.10,lambda t: .28*env(t,.1)*(.7*n(t)+.3*math.sin(math.tau*210*t)))
    write_wav("explosion",.65,lambda t: .43*env(t,.65)*(.58*n(t)+.3*math.sin(math.tau*(88*t-45*t*t))+.12*math.sin(math.tau*42*t)))
    write_wav("click",.075,lambda t: .14*env(t,.075)*math.sin(math.tau*700*t))
    def purchase(t):
        freq=(523.25,659.25,783.99)[min(2,int(t/.085))]
        local=t% .085
        return .20*min(1,local/.005)*max(0,1-local/.085)*math.sin(math.tau*freq*t)
    write_wav("purchase",.255,purchase)
    # Тихие аккорды Am / F / C / G с плавным перекрытием, без ударных.
    chords=((110.,130.8128,164.8138),(87.3071,110.,130.8128),(130.8128,164.8138,195.9977),(97.9989,123.4708,146.8324))
    length=32.
    def music(t):
        section=int(t/8)%4
        local=t%8
        blend=min(1,local/2)
        result=0.
        for chord_index,weight in (((section-1)%4,1-blend),(section,blend)):
            for j,freq in enumerate(chords[chord_index]):
                result+=weight*.026*(math.sin(math.tau*freq*t)+.22*math.sin(math.tau*freq*2*t+.8*j))
        # Длинная нота колокольчика раз в четыре секунды.
        phrase=t%4
        melody=(329.6276,391.9954,293.6648,261.6256,329.6276,523.2511,391.9954,293.6648)
        note=melody[int(t/4)%len(melody)]
        result+=.018*min(1,phrase/.12)*math.exp(-phrase/1.2)*math.sin(math.tau*note*t)
        fade=min(1,t/.5,(length-t)/.5)
        return result*max(0,fade)
    write_wav("music",length,music)


def main():
    IMAGES.mkdir(parents=True,exist_ok=True)
    AUDIO.mkdir(parents=True,exist_ok=True)
    pygame.display.init()
    for function in (player,scout,gunner,interceptor,heavy,boss,projectiles,bonuses):
        function()
    meteor("meteor_large",96,4)
    meteor("meteor_medium",60,9)
    meteor("meteor_small",32,16)
    audio()
    pygame.quit()
    print(f"Ресурсы созданы: {ROOT}")


if __name__=="__main__":
    main()
