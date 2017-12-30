import numpy as np

awg_settings = {
    'sampling_rate' : int(1e9),
    'clock_source' : 1,
    'reference_source' : 2,
    'external_reference_type' : 1,
    'trigger_source' : 1,
    'trigger_input_impedance' : 1,
    'trigger_input_threshold' : 0.5,
    'run_mode' : 4,
    'run_state' : 0,
}

for i in range(1,5):
    awg_settings[f'channel_{i}'] = {
        'channel_state' : 2,
        'analog_amplitude' : 2.0,
        'analog_offset' : 0.0,
    }

class AWG5014Handler:

    awgfile_loc = "c:\\users\\oem\\documents\\"
    awgfile_fn = "myawesomeawgfile.awg"
    awg_settings = awg_settings

    def __init__(self, awg):
        self.awg = awg

    @staticmethod
    def settings2cfg(settings):
        chan_cfg = {}
        awg_cfg = {}

        for k, v in settings.items():
            if type(v) == dict:
                chan = k[-1]
                for kk, vv in v.items():
                    chan_cfg[kk.upper() + f'_{chan}'] = vv
            else:
                awg_cfg[k.upper()] = v

        return awg_cfg, chan_cfg

    @staticmethod
    def get_awg_wf_dtype(chans=None, return_arr=False):
        if chans is None:
            chans = range(1,5)
        dtype = []
        for c in chans:
            dtype.append((f'ch{c}_wf', np.float16))
            dtype.append((f'ch{c}_m1', np.bool))
            dtype.append((f'ch{c}_m2', np.bool))

        if return_arr:
            return np.zeros((0,), dtype=dtype)

        return dtype

    def voltage_to_wfscale(self, voltage=1):
        return [voltage * 2./self.awg_settings[f'channel_{i}']['analog_amplitude'] for i in range(1,5)]


    def time_to_samples(self, time=1):
        return int(np.round(time * self.awg_settings['sampling_rate']))


    def pack_awg_wf(self, *arg, **kw):
        return self.awg.pack_waveform(*arg, **kw)


    def pack_awg_wfs(self, wfs, seq=None, autoprefix='wf'):
        """
        Packs waveforms for awg file creation.

        TODO:
            * allow sequencing with multi-use of elements (use seq)
            * naming of elements (also required for advanced sequencing)

        Parameters:

            wfs : list of dictionaries that specify sequence elements.

        Returns:

            dict : contains the information that driver method generate_awg_file wants.

        """
        wfnames = []
        nreps = []
        trig_wait = []
        goto = []
        jump = []
        packages = {}

        if seq is not None:
            # TODO: some way of specifying a sequence (probably a list of dictionaries)
            raise NotImplementedError("Nice try. Feature not yet available.")

        nwfs = len(wfs)
        for i, wf in enumerate(wfs):
            if type(wf) == tuple:
                # TODO: first element of the tuple would be the user-specified name
                raise NotImplementedError("Nice try. Feature not yet available.")

            arr = wf['wf']
            fields = [n for n in arr.dtype.fields]

            elt_names = []
            for c in range(1,5):
                if f'ch{c}_wf' in fields:
                    package = self.pack_awg_wf(arr[f'ch{c}_wf'], arr[f'ch{c}_m1'], arr[f'ch{c}_m2'])
                    idx = str(i).zfill(4)
                    name = f'{autoprefix}-{idx}_ch{c}'
                    packages[name] = package
                    elt_names.append(name)

            wfnames.append(elt_names)
            nreps.append(1)
            trig_wait.append(1 if not i else 0)
            goto.append(1 if i==nwfs-1 else 0)
            jump.append(0)

        acfg, ccfg = self.settings2cfg(self.awg_settings)

        return {
            'packed_waveforms' : packages,
            'wfname_l' : np.array(wfnames, dtype='str').T,
            'nrep' : nreps,
            'trig_wait' : trig_wait,
            'goto_state' : goto,
            'jump_to' : jump,
            'channel_cfg' : ccfg,
            'sequence_cfg' : acfg,
        }

    def program_awg(self, wfs, **kw):
        send = kw.pop('send', True)
        load = kw.pop('load', True)
        fn = kw.pop('filepath', None)

        ret = self.pack_awg_wfs(wfs, **kw)
        dawg = self.awg.generate_awg_file(**ret)

        if send:
            if fn is None:
                fn = self.awgfile_loc + self.awgfile_fn
            self.awg.send_awg_file(fn, dawg)
            if load:
                self.awg.load_awg_file(fn)
