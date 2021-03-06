# -*- coding: utf-8 -*-
"""
Created on Sun Sep 16 17:35:25 2018

@author: pang
"""
from __future__ import division

import os
import numpy as np
import random

#import richardsonpy.functions.occupancy_model as occupancy_model


class Occupancy(object):
    """
    Occupancy class of richardsonpy
    """

    # Define class variables for transition_probability_matrixes and initial 
    # occupancy 
    tpm = {}

    occ_start_states = {}
    occ_start_states_loaded = False

    type_weekday = ["wd", "we"]  # weekday, weekend

    def __init__(self, number_occupants, initial_day=1, nb_days=365,
                 do_profile=True):
        """
        Constructor of occupancy object
        
        Parameters
        ----------
        number_occupants : int
            Maximum number of occupants within apartment (range from 1 to 5)
        initial_day : int, optional
            Initial day. 1-5 correspond to Monday-Friday, 6-7 to Saturday and 
            Sunday
        nb_days : int, optional
            Number of days, which should be used to generate profile
            (default: 365)
        do_profile : bool, optional
            Defines, if user profile should be generated (default: True).
            If set to False, only number of occupants is saved and no
            profile is generated.
        """

        assert number_occupants > 0, ('At least 1 person has to be defined ' +
                                      'as occupant')
        assert number_occupants <= 5, ('Max. allowed number of occupants ' +
                                       'per apartment is 5')

        assert nb_days > 0, 'Number of days must be larger than zero.'

        assert initial_day in [1, 2, 3, 4, 5, 6, 7]

        self._kind = 'occupancy'
        self.number_occupants = number_occupants
        self.occupancy = None  # Occupancy profile
        self.initial_occupancy_h = None  
        self.initial_occupancy_a = None # Occupancy start states
        self.initial_day = initial_day

        if self.initial_day <= 5:
            self.weekend = False
        else:
            self.weekend = True

        if do_profile:
            self.gen_occ_profile(nb_days=nb_days)

    def gen_occ_profile(self, nb_days):
        """
        Generate stochastic occupancy profile based on number of occupants
        and weekday.

        Parameters
        ----------
        nb_days : int, optional
            Number of days, which should be used to generate profile
            (default: 365)
        """
       #this_path = os.path.dirname(os.path.abspath(__file__))
       #src_path = os.path.dirname(this_path)
        src_path = os.path.dirname(os.path.abspath(__file__))                  
        folder_path = os.path.join(src_path, 'inputs', 'constants')

        if not Occupancy.occ_start_states_loaded:
            # Load start states matrixes
            Occupancy.occ_start_states_loaded = True

            for weekday in self.type_weekday:
                filename = str("occ_start_states_" + weekday + ".csv")
                file_path = os.path.join(folder_path, filename)
                temp = (np.loadtxt(file_path, delimiter=";")).tolist()
                Occupancy.occ_start_states[weekday] = temp

        if not (self.number_occupants, "wd") in list(Occupancy.tpm.keys()):
            # Load transition probability matrixes
            for weekday in self.type_weekday:
                fname = str(
                    "tpm" + str(
                        self.number_occupants) + "_" + weekday + ".csv")
                file_path = os.path.join(folder_path, fname)
                temp = (np.loadtxt(file_path, delimiter=";")).tolist()
                Occupancy.tpm[self.number_occupants, weekday] = temp

        # Determine initial occupancy:
        # Determine if the current day is a weekend-day
        if self.initial_day <= 5:
            self.weekend = False
        else:
            self.weekend = True
        # Get starting states and starting probabilities
        start_states = Occupancy.occ_start_states
        start_probs = start_states[self.type_weekday[self.weekend]]
        self.initial_occupancy_a = self._get_start_state(
            start_probs[:][self.number_occupants])['aweke'] 
        self.initial_occupancy_h = self._get_start_state(
            start_probs[:][self.number_occupants])['atHome'] 
        

        # Make a full year occupancy computation
        occupancy = []
        # Loop over all days
        for i in range(nb_days):
            if (i + self.initial_day) % 7 in (0, 6):
                weekend = True
            else:
                weekend = False

            occupancy.append(self._get_occupancy(weekend))

        occupancy = np.array(occupancy)
        self.occupancy = np.reshape(occupancy, occupancy.size)


    def _get_start_state(self, start_probabilities):
        """
        Determine the active occupancy start state.
        """
        # Pick a random number to determine the start state
        f_rand = random.random()

        # Reset the cumulative probability count
        f_cumulative_p = 0

        # Return value
        result = {'atHome':0, 'awake':0}

        # Loop construction
        found = False  # Boolean variable instead of using break
        h = 0 # number of people at home 
        a = 0 # number of awake people
        # Determine the row for this state
        iRow = 7*h + a 
        

        while not found  :
            f_cumulative_p += start_probabilities[iRow]
            if (f_rand < f_cumulative_p or iRow >= len(start_probabilities) - 1):
                result['atHome'] = h
                result ['aweke'] = a
                found = True
            c = a+1
            a = c %7
            h = h+(c//7)
        return result

    def _get_occupancy(self, weekend):
        """
        """
        # Select appropriate transition probability matrix
        tpm = self.tpm[self.number_occupants, self.type_weekday[weekend]]

        # Compute occupancy for all required time steps
        occupancy = self.all_states(tpm, self.initial_occupancy_h, self.initial_occupancy_a)

        # Make the last computed occupancy the new initial value
        self.initial_occupancy = occupancy[-1]

        return occupancy
 
    ##################################################


    def all_states(tpm, initial_state_h, initial_state_a):
        """ 
            Determine the active occupancy transitions for each ten minute period 
            of the day
            
            This is a direct portation of Step 3 in the Excel-Tool 
            (module Occupancy_Model)
        """
    
        # Start with an empty result list
        result = []
        current_state_h = initial_state_h
        current_state_a = initial_state_a
        current_active_occ= min ( current_state_h, current_state_a)
        #Determine the number of possible occupancy states
        iPossibleStates = (self.number_occupants + 1) * (self.number_occupants + 1)
    
        i = 1
        
        while i <= 144:
            
            # Get a new random number
            f_rand = random.random()
            # Reset cumulative probability count
            f_cumulative_p = 0
            
            # Determine the row for this state
            iRow = iPossibleStates * (i-1) + (self.number_occupants+1) *current_state_h + current_state_a
            #Determine the last column for the transition probability matrix
            iLastColumn = iPossibleStates + 3
            # Loop construction
            j = 0
            found = False
            
           # while (not found and j <= iLastColumn):
            while (not found and j <= iLastColumn):
                f_cumulative_p = f_cumulative_p + tpm[iRow][j+3]
                if (f_rand < f_cumulative_p or i == len(tpm[iRow])-1):
                    current_state_h = j // (self.number_occupants + 1)
                    current_state_a = j % (self.number_occupants + 1)
                    current_active_occ= min ( current_state_h, current_state_a)
                    found = True
                j += 1
                current_state_h = j // (self.number_occupants + 1)
                current_state_a = j % (self.number_occupants + 1)
            
            # Store next state
            result.append(current_active_occ)
                    
            i += 1
        return result  