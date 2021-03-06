from evennia import Command as BaseCommand
from evennia import utils
import time
from random import randint
from world import rules, npc_rules
from evennia.server.sessionhandler import SESSIONS
from evennia import TICKER_HANDLER as tickerhandler
from evennia import ChannelDB

class MeleeCommand(BaseCommand):
    """
    In theory all of the attacks here will inherit from this.  This might make functions easy.

    """
    @staticmethod
    def room_type_check(self, target):
        caller = self.caller

        # rooms
        if utils.inherits_from(caller.location, "typeclasses.rooms.DeathRoom"):
            caller.msg("You can't do that now.")
            return True

        if caller.location.tags.get('city', category='corinth') and target.db.citizenship == "Corinth": # or any of the other final rooms
            caller.msg("It's not wise to attack another citizen in Corinth without approval from the Magistrates.")
            return True

    @staticmethod
    def target_type_check(self, target): # This stuff could go into a pre_command thing, shrinking the code.
        caller = self.caller

        can_attack = False
        if utils.inherits_from(target, "typeclasses.characters.Character") or utils.inherits_from(target, "typeclasses.npcs.Combat_Mob") or utils.inherits_from(target, "typeclasses.npcs.Combat_Merchant_Mob"):
            can_attack = True

        if not can_attack:
            caller.msg("You can't attack that.")
            return True

        # npc
        if utils.inherits_from(target, "typeclasses.npcs.Combat_Mob") or utils.inherits_from(target, "typeclasses.npcs.Combat_Merchant_Mob"):
            if not target.db.alive:
                caller.msg("It's dead, %s. It has to be dead." % caller.name)
                return True
            npc_rules.npc_attacked(target)
            if self.caller in target.db.offended_by:
                target.db.offended_by.remove(self.caller)
            target.db.offended_by.insert(0, self.caller)
            caller.db.last_mob_target = target

            mob_damage = caller.db.level + caller.db.current_strength
            mob_damage = float(mob_damage) * caller.db.wielding[0].db.damage_multiplier
            target.db.health = target.db.health - int(mob_damage)

            string_c, string_t, string_r = rules.weapon_attack_messages(caller, target, caller.db.wielding[0])
            caller.msg(string_c)
            target.msg(string_t)
            caller.location.msg_contents(string_r, exclude=[caller, target])

            if target.db.health <= 0:
                target.db.health = 0
                caller.msg("You have slain %s." % target.name)
                string_r = "%s falls." % target.name
                caller.location.msg_contents(string_r, exclude=[caller, target])
                rules.exp_gain(caller, target)

                target.name = target.db.defeated_name
                target.db.offended_by = []
                target.db.tries_left = target.db.tries
                tickerhandler.remove(target.db.ticker_speed, target.npc_active_ticks)
                target.db.alive = False
                tickerhandler.add(target.db.respawn_speed, target.npc_revive_ticks) # this would actually go into MeleeCommand's function for when an npc is hit.

            MeleeCommand.endurance_loss(caller, 2)
            caller.db.balance_time = time.time() + 3.5 + caller.db.wielding[0].db.balance_duration_change

            return True

    @staticmethod
    def show_balance(self):
        caller = self.caller

        # This happens if someone doesn't have balance back yet: the skill gives a message and aborts.
        if time.time() < caller.db.balance_time:
            if caller.db.balance_time - time.time() > 4:
                caller.msg("You need 4 more seconds!")
            elif caller.db.balance_time - time.time() > 3:
                caller.msg("You need 3 more seconds!")
            elif caller.db.balance_time - time.time() > 2:
                caller.msg("You need 2 more seconds!")
            elif caller.db.balance_time - time.time() > 1:
                caller.msg("You need 1 more second!")
            elif caller.db.balance_time - time.time() > 0:
                caller.msg("You've almost regained balance!")
            return True

    @staticmethod
    def hit_chance(self, target1, target2):
        #
        # Hit chance calculation goes here.
        #
        hit_chance = 75
        hit_modifier = 0

        target1_stamina = 10
        if target1.db.stamina < 10:
            hit_modifier = 10 - target1.db.stamina
            target1_stamina = target1.db.stamina # for display purposes
            hit_modifier = hit_modifier * 5
            hit_chance = hit_chance - hit_modifier

        agility_modifier = target1.db.agility - target2.db.agility
        compared_agility = agility_modifier # for display purposes

        agility_modifier = agility_modifier * 2

        hit_chance = hit_chance + agility_modifier

        d100 = randint(1, 100)

        target2_stamina = 10
        if target2.db.stamina < 10:
            adjustment = 0
            adjustment = 10 - target2.db.stamina
            target2_stamina = target2.db.stamina # for display purposes
            adjustment = adjustment * 2
            d100 = d100 - adjustment

        if target2.db.stance == "defensive":
            d100 = d100 + 40
            string_2 = ("%s seems focused on defense." % target2.name)
            #hit_chance = hit_chance - adjustment

        # This is for display purposes only now that the system has changed a few times.
        # This is for display purposes only now that the system has changed a few times.
        advantage = target1_stamina - target2_stamina
        advantage = advantage * 2
        advantage = advantage + agility_modifier

        if advantage > 0:
            string = "Offense: %s, Defense: %s. vs. Agility & Stamina: +%s advantage." % (
            hit_chance, d100, advantage)
        elif advantage < 0:
            string = "Offense: %s, Defense: %s. vs. Agility & Stamina: %s disadvantage." % (
            hit_chance, d100, advantage)
        else:
            string = "Offense: %s, Defense: %s. vs. Agility & Stamina: evenly matched." % (
            hit_chance, d100)
        target1.msg(string) # For debuggin purposes, or maybe I like it
        target2.msg(string)
        if target2.db.stance == "defensive":
            target1.msg(string_2)

        return hit_chance, d100

    def feint_roll(self, target1, target2):
        #
        # Hit chance calculation goes here.
        #
        hit_modifier = 0

        d100 = randint(1, 100)
        d100 = d100 + 25
        fake_roll = randint(1,d100)

        if target1.db.stamina < 10:
            hit_modifier = 10 - target1.db.stamina
            hit_modifier = hit_modifier * 5
            fake_roll = fake_roll - hit_modifier

        agility_modifier = target1.db.agility - target2.db.agility

        agility_modifier = agility_modifier * 2

        fake_roll = fake_roll + agility_modifier

        # if target2.db.stance == "defensive":
        #     stance_modifier = 40
        #     if target2.db.stamina < 10:
        #         adjustment = 0
        #         adjustment = 10 - target2.db.stamina
        #         adjustment = adjustment * 2
        #         stance_modifier = 40 - adjustment
        #     string_2 = ("%s seems focused on defense." % target2.name)
        #     fake_roll = fake_roll - stance_modifier

        string = "Hit Chance: %s, Roll: %s. %s Agility vs. %s Agility = %s modifier." % (fake_roll, d100, target1.db.agility, target2.db.agility, agility_modifier)
        target1.msg(string) # For debuggin purposes, or maybe I like it
        target2.msg(string)
        if target2.db.stance == "defensive":
            string_2 = ("%s seems focused on defense." % target2.name)
            target1.msg(string_2)

        return fake_roll, d100

    @staticmethod
    def damage_calc(caller, target):

        target_hp = target.db.max_health

        damage_multiplier = 2000.0 - target.db.max_health

        strength_factor = float(caller.db.strength) / 1000

        damage_multiplier = damage_multiplier * strength_factor

        damage_multiplier = damage_multiplier * 2

        damage_multiplier = damage_multiplier / 100

        damage_amount = target_hp * damage_multiplier

        damage_amount = damage_amount * caller.db.wielding[0].db.damage_multiplier

        armor_block = 100.0 - target.db.armor_bonus

        armor_block = armor_block / 100

        damage_amount = damage_amount * armor_block

        damage_amount = int(damage_amount)

        return damage_amount

    @staticmethod
    def damage_reaction(target):

        hp_ratio = float(target.db.health) / float(target.db.max_health)

        string = "%s is sent reeling!" % target.name

        if hp_ratio > 0.8:
            string = "%s weathers the blow!" % target.name
            return string
        elif hp_ratio > 0.5:
            string = "%s grunts in pain." % target.name
            return string
        elif hp_ratio > 0.2:
            string = "%s wavers bloodily on %s feet!" % (target.name, target.db.genderp)
            return string
        elif hp_ratio > 0:
            string = "%s looks as if %s is about to fall!" % (target.name, target.db.genders)
            return string

        return string

    @staticmethod
    def show_prompt(self, target):
        """
        This hook is called after the command has finished executing
        (after self.func()).
        """

        if (float(target.db.health) / float(target.db.max_health)) > 0.80:
            prompt_hp_color = "|g"
        elif (float(target.db.health) / float(target.db.max_health)) > 0.36:
            prompt_hp_color = "|y"
        else:
            prompt_hp_color = "|r"

        if target.db.stamina > 6:
            prompt_stamina_color = "|g"
        elif target.db.stamina > 3:
            prompt_stamina_color = "|y"
        else:
            prompt_stamina_color = "|r"

        magic_level = "Asleep"
        if target.db.current_magic == 0:
            magic_level = "Asleep"
        elif target.db.current_magic > 7:
            magic_level = "|rRaging|n"
        elif target.db.current_magic > 4:
            magic_level = "|yIrate|n"
        elif target.db.current_magic > 0:
            magic_level = "|gAwoken|n"

        prompt = "%sHealth|n: %s%s|n - |gMagic|n: %s|n - %sStamina|n: %s%s." % (prompt_hp_color, prompt_hp_color, target.db.health, magic_level, prompt_stamina_color, prompt_stamina_color, target.db.stamina)
        target.msg(prompt)

    @staticmethod
    def endurance_loss(caller, amount):

        # The endurance loss formula is done here.

        #caller = self.caller

        d20 = randint(1,20)

        if d20 > caller.db.endurance:
            if caller.db.stamina > amount:
                caller.db.stamina = caller.db.stamina - amount
            else:
                caller.db.stamina = 0

            if caller.db.stamina > 6:
                caller.msg(" ... You feel yourself starting to tire!")
            elif caller.db.stamina == 6 or caller.db.stamina == 5:
                caller.msg(" ... You're breathing heavily from the exertion!")
                string_E = "%s is breathing heavily from %s exertions..." % (caller.name, caller.db.genderp)
                caller.location.msg_contents(string_E, exclude=[caller])
            elif caller.db.stamina == 4 or caller.db.stamina == 3:
                caller.msg(" ... You're covered in sweat!")
                string_E = "%s is covered in sweat and breathing heavily." % caller.name
                caller.location.msg_contents(string_E, exclude=[caller])
            else:
                caller.msg(" ... You're exhausted!")
                string_E = "%s looks exhausted; as if %s can barely move!" % (caller.name, caller.db.genders)
                caller.location.msg_contents(string_E, exclude=[caller])

class CmdAssess2(MeleeCommand):
    """
    Check out your subject's wielded weapon and approximately how much stamina they have.

    Usage:
      assess <target>

    """

    key = "assess"
    aliases = ["analyze", "consider"]
    locks = "cmd:all()"
    help_category = "Melee"

    def parse(self):
        "Very trivial parser"
        self.target = self.args.strip()

    def func(self):

        caller = self.caller

        if not self.target or self.target == "here":
            caller.msg("Assess who?")
            MeleeCommand.show_prompt(self, caller)
            return
        else:
            target = caller.search(self.target)
            if not target:
                caller.msg("You cannot see %s here." % target)
                # caller.search handles error messages
                return

        if target.db.wielding:
            caller.msg("%s is wielding %s." % (target.name, target.db.wielding[0].name))
        caller.msg("You estimate that %s has %s0%% of %s stamina remaining." % (target.name, target.db.stamina, target.db.genderp))
        MeleeCommand.show_prompt(self, caller)

class CmdWielded(MeleeCommand):
    """
    Check your wielded items.

    Usage:
      wielded

    """

    key = "wielded"
    aliases = ["hands"]
    locks = "cmd:all()"
    help_category = "Melee"

    def func(self):
        caller = self.caller

        if caller.db.wielding:
            caller.msg("|wYou are currently wielding %s in your hands.|n" % (caller.db.wielding[0]))

class CmdStop(MeleeCommand):
    """
    Lower your guard.
    This command will also stops things like auto-walking.

    Usage:
      stop

    """

    key = "stop"
    aliases = ["lower", "relax"]
    locks = "cmd:all()"
    help_category = "Melee"

    def func(self):
        caller = self.caller

        if caller.db.stance == "defensive":
            caller.db.stance = "no stance"
            caller.msg("You relax your guard.")
            MeleeCommand.show_prompt(self, caller)
            return
        elif caller.db.auto_walking:
            caller.db.auto_walking = False
            caller.msg("You stop walking towards your goal.")
            return
        elif caller.db.following:
            caller.msg("You stop following %s." % caller.db.following.name)
            caller.db.following = False
        else:
            caller.msg("Stop what?")

class CmdDefend(MeleeCommand):
    """
    Assume a defensive stance, reducing the chances of taking a hit.

    Usage:
      defend

    """

    key = "defend"
    aliases = ["parry", "guard"]
    locks = "cmd:all()"
    help_category = "Melee"

    def func(self):
        caller = self.caller

        if MeleeCommand.show_balance(self):  # Checks balance, stops if you don't have it.
            return

        if not caller.db.wielding:
            caller.msg("You aren't wielding a weapon, better run instead!")
        else:
            caller.msg("|wYou raise your %s and assume a defensive stance.|n" % caller.db.wielding[
                0].db.short_name)
            string_r = ("%s raises %s %s and assumes a defensive stance." % (
            caller.name, caller.db.genderp, caller.db.wielding[0].db.short_name))
            caller.location.msg_contents(string_r, exclude=[caller])
            caller.db.stance = "defensive"

            self.endurance_loss(caller, 1)
            if caller.db.wielding:
                caller.db.balance_time = time.time() + 1 + caller.db.wielding[0].db.balance_duration_change
            else:
                caller.db.balance_time = time.time() + 1

            MeleeCommand.show_prompt(self, caller)

    # def func(self):
    #     caller = self.caller
    #
    #     if caller.db.wielding:
    #         caller.msg("|wYou are currently wielding %s in your hands.|n" % (caller.db.wielding[0]))
    #
    #         caller.location.msg_contents(string_E, exclude=[caller])

class CmdAttack(MeleeCommand):
    """
    Attack someone or something with your wielded weapon.
    The nature of the weapon and your skill with it will effect balance time, damage, wounds etc.
    The |wstance|n you and your target are in will effect hit chance, damage and speed.

    Usage:
      attack [<someone>]

    """

    key = "attack"
    aliases = ["kill", "att", "slay"]
    locks = "cmd:all()"
    help_category = "Melee"

    def parse(self):
        "Very trivial parser"
        self.target = self.args.strip()


    def func(self):

        caller = self.caller

        if not self.target or self.target == "here":
            caller.msg("Attack what?")
            return
        else:
            target = caller.search(self.target)
            if not target:
                caller.msg("You grip your weapon tightly but your foe is not here!")
                # caller.search handles error messages
                return

        if MeleeCommand.room_type_check(self, target): # Checks room type.
            return

        if MeleeCommand.show_balance(self): # Checks balance, stops if you don't have it.
            return

        if caller.db.moving:
            caller.msg("You are already moving away!")
            return

        if caller.db.wielding and utils.inherits_from(caller.db.wielding[0], "typeclasses.arms.Weapons"):
            weapon_name = caller.db.wielding[0].db.short_name
        else:
            caller.msg("You aren't wielding a weapon!")
            return

        if caller.db.stamina == 0: # Checks stamina, stops if you don't have it.
            caller.msg("You are too tired to swing your weapon!")
            MeleeCommand.show_prompt(self, caller)
            return

        if MeleeCommand.target_type_check(self, target):
            MeleeCommand.show_prompt(self, caller)
            return

        # if utils.inherits_from(caller.db.wielding, "typeclasses.arms.Weapons"):
        #     weapon_name = caller.db.wielding.short_name
        # else:
        #     caller.msg("You aren't wielding a weapon!")
        #     return
        # also the shield spell's bounce should go in

        caller.db.stance = "no stance"

        if target.db.shielded:
            string_c = "The magic circle surrounding %s shields %s from harm." % (target.name, target.db.gendero)
            caller.msg(string_c)
            MeleeCommand.show_prompt(self, caller)
            return

        damage_calc = MeleeCommand.damage_calc(caller, target)
        hit_chance, d100 = MeleeCommand.hit_chance(self, caller, target)

        if hit_chance > d100:

            # Hit messages.
            string_c, string_t, string_r = rules.weapon_attack_messages(caller, target, caller.db.wielding[0])
            caller.msg(string_c)
            target.msg(string_t)
            caller.location.msg_contents(string_r, exclude=[caller, target])

            string_T = " ... You lose |r%s|n health!" % damage_calc
            target.msg(string_T)
            target.db.health = target.db.health - damage_calc
            if target.db.health > 0:
                string = MeleeCommand.damage_reaction(target)
                string_c = "|w" + string + "|n"
                caller.msg(string_c)
                caller.location.msg_contents(string, exclude=[caller, target])
            if target.db.health <= 0 and not target.db.immortal:
                target.db.health = 0
                rules.death_movement(caller, target)
                string = "|r%s has been slain by %s.|n" % (target.name, caller.name)
                rage = ChannelDB.objects.get_channel("rage")
                rage.msg(string)
                rules.exp_gain(caller, target)

            MeleeCommand.endurance_loss(caller, 3)
            if caller.db.wielding:
                caller.db.balance_time = time.time() + 3.5 + caller.db.wielding[0].db.balance_duration_change
            else:
                caller.db.balance_time = time.time() + 3.5
        else:
            string_c, string_t, string_r = rules.weapon_miss_messages(caller, target, caller.db.wielding[0])
            caller.msg(string_c)
            target.msg(string_t)
            caller.location.msg_contents(string_r, exclude=[caller, target])

            self.endurance_loss(caller, 1)

            if caller.db.wielding:
                caller.db.balance_time = time.time() + 2.25 + caller.db.wielding[0].db.balance_duration_change
            else:
                caller.db.balance_time = time.time() + 2.25

        # Show both prompts
        MeleeCommand.show_prompt(self, caller)
        MeleeCommand.show_prompt(self, target)

class CmdMaul(MeleeCommand):
    """
    Maul someone you don't like, if you're Ashlan.

    Usage:
      maul [<someone>]

    """

    key = "maul"
    #aliases = ["kill", "att"]
    locks = "cmd:id(4)"
    help_category = "Melee"

    def parse(self):
        "Very trivial parser"
        self.target = self.args.strip()

    def func(self):

        caller = self.caller
        target = self.target

        if MeleeCommand.target_type_check(self, target): # Checks room type.
            return

        if not self.target or self.target == "here":
            caller.msg("Attack what?")
            return
        else:
            target = caller.search(self.target)
            if not target:
                caller.msg("%s isn't here to maul." % target.name)
                # caller.search handles error messages
                return

        if MeleeCommand.show_balance(self): # Checks balance, stops if you don't have it.
            return

        if caller.db.stamina == 0: # Checks stamina, stops if you don't have it.
            caller.msg("You are too tired to maul anyone else!")
            MeleeCommand.show_prompt(self, caller)
            return

        if caller.db.moving == True:
            caller.msg("You're walking the other way!")
            return

        # if utils.inherits_from(caller.db.wielding, "typeclasses.arms.Weapons"):
        #     weapon_name = caller.db.wielding.short_name
        # else:
        #     caller.msg("You aren't wielding a weapon!")
        #     return
        # also the shield spell's bounce should go in

        caller.db.stance = "no stance"

        damage_calc = 9001
        #hit_chance, d100 = MeleeCommand.hit_chance(self, caller, target)
        hit_chance = 777
        d100 = 0

        if hit_chance > d100:

            string_t = "Offense: 777, Defense: 1. Infinite Agility vs. %s Agility = doesn't really matter does it?" % target.db.agility
            target.msg(string_t)
            # Hit messages.
            #string_c, string_t, string_r = rules.weapon_attack_messages(caller, target, caller.db.wielding[0])
            string_c = "|wYou leap onto %s and maul the s- out of %s.|n" % (target.name, target.db.gendero)
            string_t = "Ashlan leaps onto you and mauls the s- out of you."
            string_r = "Ashlan leaps onto %s and mauls the s- out of %s." % (target.name, target.db.gendero)
            caller.msg(string_c)
            target.msg(string_t)
            caller.location.msg_contents(string_r, exclude=[caller, target])

            string_T = " ... You lose |r%s|n health!" % damage_calc
            target.msg(string_T)
            target.db.health = target.db.health - damage_calc
            if target.db.health <= 0:
                #target.msg("You would have died if death was coded in!")
                target.db.health = 0
                rules.death_movement(caller, target)
                string = "|rAshlan just mauled the s- out of %s.|n" % target.name
                rage = ChannelDB.objects.get_channel("rage")
                rage.msg(string)
                #caller.msg("You would have slain %s if death was coded in!" % target.name)

            MeleeCommand.endurance_loss(caller, 3)
            caller.db.balance_time = time.time() + 3.5 + caller.db.wielding[0].db.balance_duration_change
        else:
            string_c, string_t, string_r = rules.weapon_miss_messages(caller, target, caller.db.wielding[0])
            caller.msg(string_c)
            target.msg(string_t)
            caller.location.msg_contents(string_r, exclude=[caller, target])

            self.endurance_loss(caller, 1)
            caller.db.balance_time = time.time() + 2.25 + caller.db.wielding[0].db.balance_duration_change

        # Show both prompts
        MeleeCommand.show_prompt(self, caller)
        MeleeCommand.show_prompt(self, target)

class CmdFeint(MeleeCommand):
    """
    Make a fake attack towards your target. This will reduce your stamina by less than a real attack and take less time.
    If you are in a defensive stance, this will not disrupt that, unlike a real attack.

    Usage:
        feint <target>

    A skilled opponent may detect that your move is a feint.
    """

    key = "feint"
    aliases = ["threat"]
    locks = "cmd:all()"
    help_category = "Melee"

    def parse(self):
        "Very trivial parser"
        self.target = self.args.strip()


    def func(self):

        caller = self.caller

        if MeleeCommand.room_type_check(self): # Checks room type.
            return

        if not self.target or self.target == "here":
            caller.msg("Feint towards what?")
            return
        else:
            target = caller.search(self.target)
            if not target:
                caller.msg("You grip your weapon tightly but your foe is not in range!")
                # caller.search handles error messages
                return

        if MeleeCommand.show_balance(self): # Checks balance, stops if you don't have it.
            return

        if caller.db.stamina == 0: # Checks stamina, stops if you don't have it.
            caller.msg("You are too tired to swing your weapon!")
            MeleeCommand.show_prompt(self, caller)
            return

        # if utils.inherits_from(caller.db.wielding, "typeclasses.arms.Weapons"):
        #     weapon_name = caller.db.wielding.short_name
        # else:
        #     caller.msg("You aren't wielding a weapon!")
        #     return
        # also the shield spell's bounce should go in

        if caller.db.wielding and utils.inherits_from(caller.db.wielding[0], "typeclasses.arms.Weapons"):
            weapon_name = caller.db.wielding[0].db.short_name
        else:
            caller.msg("You aren't wielding a weapon!")
            return

        caller.msg("You make a feint towards %s." % target.name)
        hit_chance, d100 = MeleeCommand.feint_roll(self, caller, target)

        if hit_chance:

            # Hit messages.
            string_c, string_t, string_r = rules.weapon_attack_messages(caller, target, caller.db.wielding[0])
            caller.msg(string_c)
            target.msg(string_t)
            caller.location.msg_contents(string_r, exclude=[caller, target])

            string_c, string_t, string_r = rules.weapon_miss_messages(caller, target, caller.db.wielding[0])
            caller.msg(string_c)
            target.msg(string_t)
            caller.location.msg_contents(string_r, exclude=[caller, target])

            self.endurance_loss(caller, 1)
            half_balance = caller.db.wielding[0].db.balance_duration_change / 2
            caller.db.balance_time = time.time() + 1 + half_balance

        # Show both prompts
        MeleeCommand.show_prompt(self, caller)
        MeleeCommand.show_prompt(self, target)


















#####################################################
# Old Attack command with telegraphed delays below.
#####################################################


# It seems as if evennia's "yield" function is a better way to create delayed action commands.