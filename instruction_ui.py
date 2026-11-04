"""Draw instruction bubbles near objects in the level."""
import pygame


def draw_instruction(screen, font, lines, anchor):
    texts = [font.render(line, True, (241,249,237)) for line in lines]
    width = max(text.get_width() for text in texts) + 36
    height = len(texts) * 25 + 22
    box = pygame.Rect(0, 0, width, height)
    box.midbottom = (round(anchor[0]), round(anchor[1]) - 22)
    box.clamp_ip(screen.get_rect().inflate(-20, -20))
    panel = pygame.Surface((width, height + 18), pygame.SRCALPHA)
    fill, border = (12,30,38,242), (183,222,191,255)
    tip = max(22, min(width-22, round(anchor[0])-box.x))
    points = [(tip-12,height-2),(tip,height+15),(tip+12,height-2)]
    pygame.draw.polygon(panel, fill, points)
    pygame.draw.lines(panel, border, False, points, 2)
    pygame.draw.rect(panel, fill, (0,0,width,height), border_radius=16)
    pygame.draw.rect(panel, border, (0,0,width,height), 2, border_radius=16)
    for i, text in enumerate(texts):
        panel.blit(text, (18,11+i*25))
    screen.blit(panel, box.topleft)
    return box
