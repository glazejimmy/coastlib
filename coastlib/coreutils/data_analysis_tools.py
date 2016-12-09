import math
import pandas as pd
import statsmodels.api as sm
import numpy as np
import datetime
import scipy.stats as sps
import matplotlib.pyplot as plt
import warnings


class DelSepData:
    """
    A Delimeter Sepatared Data (general case of CSV-type files) class.
    Creates a Pandas DataFrame for the extracted data.
    """
    def __init__(self, path, delimeter=',', label_delimeter=' ',
                 void_rows=1, date_type='yyyymmdd_hhmm', sort=True, **kwargs):
        """
        :param path: str
            Path to data file.
        :param delimeter: str
        :param void_rows: int
            Number of first consecutive rows (followed by a row with column labels)
            containing irrelevant data.
        :param date_type: str
            Datetime type for indexing purposed. See .gen_index() method.
            Set to None to skip this step. Default = yyyymmdd_hhmm.
        :param sort: bool
            Sorts by index if True.
        """
        with open(path, 'r') as file:
            data = [line.split(delimeter) for line in file]
        if void_rows > 0:
            data = data[void_rows:]
        if label_delimeter == ' ':
            labels = [var for var in data[0][0].split(' ') if len(var) > 0][0:-1]
        elif label_delimeter == ',':
            labels = [var for var in data[0]][:-1]
        del data[0]
        for i in range(len(data)):
            data[i] = data[i][0:-1]
            for j in range(len(data[i])):
                data[i][j] = data[i][j].replace(' ', '')
                try:
                    data[i][j] = float(data[i][j])
                    if data[i][j] % 1 == 0:
                        data[i][j] = int(data[i][j])
                except ValueError:
                    pass
                if data[i][j] == '':
                    data[i][j] = np.nan
        self.data = pd.DataFrame(data=data, columns=labels)
        if date_type == 'yyyymmdd_hhmm':
            self.gen_index(
                date_type=date_type,
                yyyymmdd=kwargs.pop('yyyymmdd', 'Date'),
                hhmm=kwargs.pop('hhmm', 'HrMn')
            )
        elif date_type is None:
            pass
        else:
            raise ValueError('Unrecognized date type.')
        if sort:
            self.data.sort_index(inplace=True)

    def gen_index(self, date_type='yyyymmdd_hhmm', **kwargs):
        """
        Generates datetime indexes and applies them to DataFrame.

        :param date_type: str
        :param kwargs:
            yyyymmdd: str
                Column name. Default = Date.
            hhmm: str
                Column name. Default = HrMn.
        """
        if date_type == 'yyyymmdd_hhmm':
            yyyymmdd = kwargs.pop('yyyymmdd', 'Date')
            hhmm = kwargs.pop('hhmm', 'HrMn')
            dates = [str(int(i)) for i in self.data[yyyymmdd].values]
            times = [str(int(i)) for i in self.data[hhmm].values]
            years = [int(i[0:4]) for i in dates]
            months = [int(i[4:6]) for i in dates]
            days = [int(i[6:8]) for i in dates]
            minutes = [int(i) % 100 for i in times]
            hours = [int(int(i) / 100) for i in times]
            del self.data[yyyymmdd]
            del self.data[hhmm]
        else:
            raise ValueError('Unrecognized date type.')
        time = []
        for i in range(len(self.data)):
            time += [
                datetime.datetime(year=years[i],
                                  month=months[i],
                                  day=days[i],
                                  hour=hours[i],
                                  minute=minutes[i]
                                  )
            ]
        self.data.set_index([time], inplace=True)


def joint_probability(df, **kwargs):
    """
    Generates a joint probability table of 2 variables.

    Parameters
    ----------
    df : dataframe
        Pandas dataframe
    val1, val2 : str
        Column names in df
    binsize1, binsize2 : float
        Bin sizes for variables val1 and val2
    savepath, savename : str
        Save folder path and file save name
    output_format : str
        Joint table values (absolute 'abs' or relative / percent 'rel')
    """
    val1 = kwargs.pop('val1', 'Hs')
    val2 = kwargs.pop('val2', 'Tp')
    binsize1 = kwargs.pop('binsize1', 0.3)
    binsize2 = kwargs.pop('binsize2', 4)
    savepath = kwargs.pop('savepath', None)
    savename = kwargs.pop('savename', 'Joint Probability')
    output_format = kwargs.pop('output_format', 'rel')
    assert len(kwargs) == 0, 'unrecognized arguments passed in: {}'.format(', '.join(kwargs.keys()))

    a = df[pd.notnull(df[val1])]
    a = a[pd.notnull(a[val2])]
    bins1 = math.ceil(a[val1].max() / binsize1)
    bins2 = math.ceil(a[val2].max() / binsize2)
    columns = []
    rows = []
    for i in range(bins1):
        low = i * binsize1
        up = low + binsize1
        columns += ['{0:.1f} - {1:.1f}'.format(low, up)]
    for i in range(bins2):
        low = i * binsize2
        up = low + binsize2
        rows += ['{0:.1f} - {1:.1f}'.format(low, up)]
    if output_format == 'abs':
        jp_raw = pd.DataFrame(0, index=rows, columns=columns)
    else:
        jp_raw = pd.DataFrame(.0, index=rows, columns=columns)

    tot = len(a)
    for i in range(bins2):
        bin2_low = i * binsize2
        bin2_up = bin2_low + binsize2
        for j in range(bins1):
            bin1_low = j * binsize1
            bin1_up = bin1_low + binsize1
            b = len(
                a[
                    (a[val1] < bin1_up) &
                    (a[val1] >= bin1_low) &
                    (a[val2] < bin2_up) &
                    (a[val2] >= bin2_low)
                ]
            )
            if output_format == 'abs':
                jp_raw[columns[j]][i] = b
            elif output_format == 'rel':
                jp_raw[columns[j]][i] = b / tot
            else:
                raise ValueError('output format should be either *abs* or *rel*')
    if savepath is not None:
        jp_raw.to_excel(pd.ExcelWriter(savepath + '\\' + savename + '.xlsx'), sheet_name='joint_prob', )
    else:
        return jp_raw


def associated_value(df, val, par, value, search_range=0.1):
    """
    For datframe df, value *val* (i.e. 'Hs') and parameter *par* (i.e. 'Tp')
    returns parameter value statistically associated with *val* *value*
    """
    df = df[pd.notnull(df[val])]
    df = df[pd.notnull(df[par])]
    val_range = df[val].max() - df[val].min()
    a_low = value - search_range * val_range
    a_up = value + search_range * val_range
    a = df[(df[val] > a_low) & (df[val] < a_up)]
    par_array = a[par].as_matrix()
    dens = sm.nonparametric.KDEUnivariate(par_array)
    dens.fit()
    return dens.support[dens.density.argmax()]


class EVA:
    """
    Extreme Value Analysis class. Takes a Pandas DataFrame with values. Extracts extreme values.
    Assists with threshold value selection. Fits data to distributions (GPD).
    Returns extreme values' return periods. Generates data plots.
    """
    def __init__(self, df, col=None, handle_nans=True, usetex=False):
        """
        :param df: DataFrame or Series
            Pandas DataFrame or Series object with column 'col' containing values and indexes as datetime.
        :param col: str
            Column name for the variable of interest (i.e. 'Spd').
            Default = None (takes first column as variables = df.columns[0]).
        """
        if type(df) != type(pd.DataFrame()):
            try:
                self.data = df.to_frame()
            except:
                raise ValueError('Invalid data type in <df>. This class takes only Pandas DataFrame or Series objects.')
        else:
            self.data = df
        if col is not None:
            self.col = col
        else:
            self.col = df.columns[0]
        self.extremes = 'NO VALUE! Run the .get_extremes() method first.'
        self.method = 'NO VALUE! Run the .get_extremes() method first.'
        self.threshold = 'NO VALUE! Run the .get_extremes() method first.'
        self.distribution = 'NO VALUE! Run the .fit() method first.'
        self.retvalsum = 'Run the .fit() method first.'
        self.usetex = usetex
        # Calculate number of years in data
        self.N = len(np.unique(self.data.index.year))
        if handle_nans:

            def numbify(x):
                try:
                    return float(x)
                except:
                    return 999

            self.data[self.col] = self.data[self.col].apply(numbify)
            self.data = self.data[self.data[self.col] != 999.999]
            self.data = self.data[self.data[self.col] != 999.9]
            self.data = self.data[self.data[self.col] != 999]
            self.data = self.data[pd.notnull(self.data[self.col])]

    def get_extremes(self, method='POT', **kwargs):
        """
        Extracts extreme values.

        :param method: str
            Extraction method. POT for Peaks Over Threshold, BM for Block Maxima.
        :param kwargs:
            u : float
                Threshold value (POT method only). Default = 90 percentile.
            r : float
                Minimum independent event distance (hours) (POT method only). Default = 24 hours.
            decluster : bool
                Specify if extreme values are declustered (POT method only). Default = True.
            block : timedelta
                Block size (years) (BM method only). Default = 1 year.
        :return:
            self.extremes : DataFrame
                A DataFrame with extracted extreme values and Weibull return periods.
        """
        if method == 'POT':
            self.method = 'POT'
            u = kwargs.pop('u', np.percentile(self.data[self.col], 90))
            r = kwargs.pop('r', 24)
            decluster = kwargs.pop('decluster', True)
            assert len(kwargs) == 0, 'unrecognized arguments passed in: {}'.format(', '.join(kwargs.keys()))
            self.extremes = self.data[self.data[self.col] >= u]
            if decluster:
                r = datetime.timedelta(hours=r)
                indexes = self.extremes.index
                new_extremes = self.extremes.loc[indexes[0]:indexes[0]]
                for date in indexes:
                    if date - new_extremes.index[-1] >= r:
                        new_extremes = pd.concat([new_extremes, self.extremes.loc[date:date]])
                    else:
                        if self.extremes.loc[date:date][self.col].values[0] > new_extremes[self.col].values[-1]:
                            new_extremes = new_extremes.drop(new_extremes.index[len(new_extremes) - 1])
                            new_extremes = pd.concat([new_extremes, self.extremes.loc[date:date]])
                self.extremes = new_extremes
            self.threshold = u
        elif method == 'BM':
            self.method = 'BM'
            block = kwargs.pop('block', 'Y')
            assert len(kwargs) == 0, 'unrecognized arguments passed in: {}'.format(', '.join(kwargs.keys()))
            years = np.unique(self.data.index.year)
            # months = np.array([np.unique(self.data[self.data.index.year == year].index.month) for year in years])
            if block == 'Y':
                bmextremes = [self.data[self.data.index.year == year].drop_duplicates(self.col) for year in years]
                bmextremes = [x[x[self.col] == x[self.col].max()] for x in bmextremes]
                self.extremes = pd.concat(bmextremes)
            elif block == 'M':
                raise NotImplementedError('Not yet implemented')
            elif block == 'W':
                raise NotImplementedError('Not yet implemented')
            else:
                raise ValueError('Unrecognized block size')
        else:
            raise ValueError('Unrecognized extremes parsing method. Use POT or BM methods.')
        self.extremes.sort_values(by=self.col, inplace=True)
        cdf = np.arange(len(self.extremes)) / len(self.extremes)
        return_periods = (self.N + 1) / (len(self.extremes) * (1 - cdf))
        self.extremes['T'] = pd.DataFrame(index=self.extremes.index, data=return_periods)
        self.extremes.sort_index(inplace=True)

    def pot_residuals(self, u, decluster=True, r=24, save_path=None, name='_DATA_SOURCE_'):
        """
        Calculates mean residual life values for different threshold values.

        :param u: list
            List of threshold to be tested
        :param plot: bool
            Plot residuals against threshold values. Default = False
        :param save_path: str
            Path to folder. Default = None.
        :param name: str
            Plot name.
        :param decluster: bool
            Decluster data using the run method.
        :param r: float
            Decluster run length (Default = 24 hours).
        :return:
        """
        u = np.array(u)
        if u.max() > self.data[self.col].max():
            u = u[u <= self.data[self.col].max()]
        if decluster:
            nu = []
            res_ex_sum = []
            for i in range(len(u)):
                self.get_extremes(method='POT', u=u[i], r=r, decluster=True)
                nu += [len(self.extremes[self.col].values)]
                res_ex_sum += [self.extremes[self.col].values - u[i]]
        else:
            nu = [len(self.data[self.data[self.col] >= i]) for i in u]
            res_ex_sum = [(self.data[self.data[self.col] >= u[i]][self.col] - u[i]).values for i in range(len(u))]
        residuals = [(sum(res_ex_sum[i]) / nu[i]) for i in range(len(u))]
        intervals = [sps.norm.interval(0.95, loc=res_ex_sum[i].mean(), scale=res_ex_sum[i].std() / len(res_ex_sum[i]))
                     for i in range(len(u))]
        intervals_u = [intervals[i][0] for i in range(len(intervals))]
        intervals_l = [intervals[i][1] for i in range(len(intervals))]
        with plt.style.context('bmh'):
            plt.figure(figsize=(16, 8))
            plt.subplot(1, 1, 1)
            if self.usetex:
                plt.plot(u, residuals, lw=2, color='orangered', label=r'$\textbf{Mean Residual Life}$')
                plt.fill_between(u, intervals_u, intervals_l, alpha=0.3, color='royalblue',
                                 label=r'$\textbf{95\% confidence interval}$')
                plt.xlabel(r'$\textbf{Threshold Value}$')
                plt.ylabel(r'$\textbf{Mean residual Life}$')
                plt.title(r'$\textbf{{{} Mean Residual Life Plot}}$'.format(name))
            else:
                plt.plot(u, residuals, lw=2, color='orangered', label=r'Mean Residual Life')
                plt.fill_between(u, intervals_u, intervals_l, alpha=0.3, color='royalblue',
                                 label=r'95% confidence interval')
                plt.xlabel(r'Threshold Value')
                plt.ylabel(r'Mean residual Life')
                plt.title(r'{} Mean Residual Life Plot'.format(name))
            plt.legend()
        if save_path is not None:
            plt.savefig(save_path + '\{} Mean Residual Life.png'.format(name), bbox_inches='tight', dpi=600)
            plt.close()
        else:
            plt.show()

    def empirical_threshold(self, decluster=False, r=24, u_step=0.1, u_start=0):
        """
        Get exmpirical threshold extimates for 3 methods: 90% percentile value,
        square root method, log-method.

        :param decluster:
            Determine if declustering is used for estimating thresholds.
            Very computationally intensive.
        :param r:
            Declustering run length parameter.
        :param u_step:
            Threshold precision.
        :param u_start:
            Starting threshold for search (should be below the lowest expected value).
        :return:
            DataFrame with threshold summary.
        """
        tres = [np.percentile(self.data[self.col].values, 90)]
        k = int(np.sqrt(len(self.data)))
        u = u_start
        if decluster:
            self.get_extremes(method='POT', u=u, r=r, decluster=True)
            while len(self.extremes) > k:
                u += u_start
                self.get_extremes(method='POT', u=u, r=r, decluster=True)
        else:
            self.get_extremes(method='POT', u=u, r=r, decluster=False)
            while len(self.extremes) > k:
                u += u_step
                self.get_extremes(method='POT', u=u, r=r, decluster=False)
        tres += [u]
        k = int((len(self.data) ** (2 / 3)) / np.log(np.log(len(self.data))))
        u = u_start
        if decluster:
            self.get_extremes(method='POT', u=u, r=r, decluster=True)
            while len(self.extremes) > k:
                u += u_step
                self.get_extremes(method='POT', u=u, r=r, decluster=True)
        else:
            self.get_extremes(method='POT', u=u, r=r, decluster=False)
            while len(self.extremes) > k:
                u += u_step
                self.get_extremes(method='POT', u=u, r=r, decluster=False)
        tres += [u]
        return pd.DataFrame(data=tres, index=['90% Quantile', 'Squre Root Rule', 'Logarithm Rule'],
                            columns=['Threshold'])

    def par_stab_plot(self, u, decluster=True, r=24, save_path=None, name='_DATA_SOURCE_'):
        """
        Generates a parameter stability plot for the a range of thresholds u.
        :param u: list or array
            List of threshold values.
        :param decluster: bool
            Use run method to decluster data 9default = True)
        :param r: float
            Run lengths (hours), specify if decluster=True.
        :param save_path: str
            Path to save folder.
        :param name: str
            File save name.
        """
        u = np.array(u)
        if u.max() > self.data[self.col].max():
            u = u[u <= self.data[self.col].max()]
        fits = []
        if decluster:
            for tres in u:
                self.get_extremes(method='POT', u=tres, r=r, decluster=True)
                extremes_local = self.extremes[self.col].values - tres
                fit = sps.genpareto.fit(extremes_local, loc=tres)
                fits += [fit]
        else:
            for tres in u:
                self.get_extremes(method='POT', u=tres, r=r, decluster=False)
                extremes_local = self.extremes[self.col].values - tres
                fit = sps.genpareto.fit(extremes_local, loc=tres)
                fits += [fit]
        shapes = [x[0] for x in fits]
        scales = [x[2] for x in fits]
        scales_mod = [scales[i] - shapes[i] * u[i] for i in range(len(u))]
        with plt.style.context('bmh'):
            plt.figure(figsize=(16, 8))
            plt.subplot(1, 2, 1)
            if self.usetex:
                plt.plot(u, shapes, lw=2, color='orangered', label=r'$\textbf{Shape Parameter}$')
                plt.xlabel(r'$\textbf{Threshold Value}$')
                plt.ylabel(r'$\textbf{Shape Parameter}$')
                plt.subplot(1, 2, 2)
                plt.plot(u, scales_mod, lw=2, color='orangered', label=r'$\textbf{Modified Scale Parameter}$')
                plt.xlabel(r'$\textbf{Threshold Value}$')
                plt.ylabel(r'$\textbf{Modified Scale Parameter}$')
                plt.suptitle(r'$\textbf{{{} Parameter Stability Plot}}$'.format(name))
            else:
                plt.plot(u, shapes, lw=2, color='orangered', label=r'Shape Parameter')
                plt.xlabel(r'Threshold Value')
                plt.ylabel(r'Shape Parameter')
                plt.subplot(1, 2, 2)
                plt.plot(u, scales_mod, lw=2, color='orangered', label=r'Modified Scale Parameter')
                plt.xlabel(r'Threshold Value')
                plt.ylabel(r'Modified Scale Parameter')
                plt.suptitle(r'{} Parameter Stability Plot'.format(name))
        if save_path is not None:
            plt.savefig(save_path + '\{} Parameter Stability Plot.png'.format(name), bbox_inches='tight', dpi=600)
            plt.close()
        else:
            plt.show()

    def fit(self, distribution='GPD', confidence=False, k=10**2, trunc=True):
        """
        Implemented: GEV, GPD

        Fits distribution to data and generates a summary dataframe (required for plots).
        :param distribution:
            Distribution name (default 'GPD'). Available: GPD, GEV, Gumbel, Wibull, log-normal, Pearson 3
        :param confidence: bool
            Calculate 95% confidence limits using Monte Carlo simulation
            !!!!    (WARNING! Might be time consuming for large k)    !!!!
            Be cautious with interpreting the 95% confidence limits.
            Implemented for GPD, GEV
        :param k: int
            Number of Monte Carlo simulations (default k=10^4, try 10^2 before committing to 10^4).
        :param trunc: bool
            Truncate Monte Carlo generated fits by discarding fits with return values larger
            than the values for "true" fit for return periods multiplied by *k* (i.e. discards "bad" fits)
        :return: DataFrame
            self.retvalsum summary dataframe with fitted distribution and 95% confidence limits.
        """
        self.distribution = distribution
        if self.distribution == 'GPD':
            if self.method == 'POT':
                def ret_val(t, param, rate, u):
                    return u + sps.genpareto.ppf(1 - 1 / (rate * t), c=param[0], loc=param[1], scale=param[2])
                parameters = sps.genpareto.fit(self.extremes[self.col].values - self.threshold)
            else:
                def ret_val(t, param, rate, u):
                    return sps.genpareto.ppf(1 - 1 / (rate * t), c=param[0], loc=param[1], scale=param[2])
                parameters = sps.genpareto.fit(self.extremes[self.col].values)
        elif self.distribution == 'GEV':
            if self.method != 'BM':
                raise ValueError('GEV distribution is applicable only with the BM method')
            def ret_val(t, param, rate, u):
                return sps.genextreme.ppf(1 - 1 / (rate * t), c=param[0], loc=param[1], scale=param[2])
            parameters = sps.genextreme.fit(self.extremes[self.col].values)

        # NOT IMPLEMENTED
        elif self.distribution == 'Gumbel':
            if self.method != 'BM':
                raise ValueError('Gumbel distribution is applicable only with the BM method')
            def ret_val(t, param, rate, u):
                return u + sps.gumbel_r.ppf(1 - 1 / (rate * t), loc=param[0], scale=param[1])
            parameters = sps.gumbel_r.fit(self.extremes[self.col].values - self.threshold)
        elif self.distribution == 'Weibull':
            def ret_val(t, param, rate, u):
                return u + sps.weibull_min.ppf(1 - 1 / (rate * t), c=param[0], loc=param[1], scale=param[2])
            parameters = sps.weibull_min.fit(self.extremes[self.col].values - self.threshold)
        elif self.distribution == 'Log-normal':
            def ret_val(t, param, rate, u):
                return u + sps.lognorm.ppf(1 - 1 / (rate * t), s=param[0], loc=param[1], scale=param[2])
            parameters = sps.lognorm.fit(self.extremes[self.col].values - self.threshold)
        elif self.distribution == 'Pearson 3':
            def ret_val(t, param, rate, u):
                return u + sps.pearson3.ppf(1 - 1 / (rate * t), skew=param[0], loc=param[1], scale=param[2])
            parameters = sps.pearson3.fit(self.extremes[self.col].values - self.threshold)
        else:
            raise ValueError('Distribution type not recognized.')
        # NOT IMPLEMENTED

        rp = np.unique(np.append(np.logspace(-1, 3, num=30), [2, 5, 10, 25, 50, 100, 200, 500]))
        rate = len(self.extremes) / self.N
        rv = ret_val(rp, param=parameters, rate=rate, u=self.threshold)
        self.retvalsum = pd.DataFrame(data=rv, index=rp, columns=['Return Value'])
        self.retvalsum.index.name = 'Return Period'

        if confidence:
            lex = len(self.extremes)
            # Monte Carlo return values generator
            if self.distribution == 'GPD':
                def montefit():
                    loc_lex = sps.poisson.rvs(lex)
                    sample = sps.genpareto.rvs(c=parameters[0], loc=parameters[1], scale=parameters[2], size=loc_lex)
                    loc_rate = loc_lex / self.N
                    loc_param = sps.genpareto.fit(sample, floc=parameters[1])
                    return ret_val(rp, param=loc_param, rate=loc_rate, u=self.threshold)
            elif self.distribution == 'GEV':
                def montefit():
                    sample = sps.genextreme.rvs(c=parameters[0], loc=parameters[1], scale=parameters[2], size=ex)
                    loc_rate = lex / self.N
                    loc_param = sps.genextreme.fit(sample, floc=parameters[1])
                    return ret_val(rp, param=loc_param, rate=loc_rate, u=self.threshold)
            else:
                raise ValueError('Distribution type not recognized.')
            sims = 0
            mrv = []
            if trunc:
                uplims = ret_val(k * rp, param=parameters, rate=rate, u=self.threshold)
                while sims < k:
                    x = montefit()
                    if (x > uplims).sum() == 0:
                        mrv += [x]
                        sims += 1
            else:
                while sims < k:
                    mrv += [montefit()]
                    sims += 1
            mrv_pivot = [[mrv[i][j] for i in range(len(mrv))] for j in range(len(rp))]
            moments = [sps.norm.fit(x) for x in mrv_pivot]
            intervals = [sps.norm.interval(alpha=0.95, loc=x[0], scale=x[1]) for x in moments]
            self.retvalsum['Lower'] = pd.Series(data=[x[0] for x in intervals], index=rp)
            self.retvalsum['Upper'] = pd.Series(data=[x[1] for x in intervals], index=rp)
        self.retvalsum.dropna(inplace=True)

    def ret_val_plot(self, confidence=False, save_path=None, name='_DATA_SOURCE_', **kwargs):
        """
        Creates return value plot (return periods vs return values)

        :param confidence: bool
            True if confidence limits were calculated in the .fit() method.
        :param save_path: str
        :param name: str
        :param kwargs:
            unit: str
                Return value unit (i.e. m/s) default = unit
            ylim: tuple
                Y axis limits (to avoid showing entire confidence limit range). Default=(0, ReturnValues.max()).
        :return:
        """
        unit = kwargs.pop('unit', 'unit')
        ylim = kwargs.pop('ylim', (0, int(self.retvalsum['Return Value'].values.max())))
        assert len(kwargs) == 0, 'unrecognized arguments passed in: {}'.format(', '.join(kwargs.keys()))
        with plt.style.context('bmh'):
            plt.figure(figsize=(16, 8))
            plt.subplot(1, 1, 1)
            if self.usetex:
                plt.scatter(self.extremes['T'].values, self.extremes[self.col].values, s=20, linewidths=1,
                            marker='o', facecolor='None', edgecolors='royalblue', label=r'$\textbf{Extreme Values}$')
                plt.plot(self.retvalsum.index.values, self.retvalsum['Return Value'].values,
                         lw=2, color='orangered', label=r'$\textbf{{{} Fit}}$'.format(self.distribution))
                if confidence:
                    plt.fill_between(self.retvalsum.index.values, self.retvalsum['Upper'].values,
                                     self.retvalsum['Lower'].values, alpha=0.3, color='royalblue',
                                     label=r'$\textbf{95\% confidence interval}$')
                plt.xscale('log')
                plt.xlabel(r'$\textbf{Return Period}\, [\textit{years}]$')
                plt.ylabel(r'$\textbf{{Return Value}}\, [\textit{{{0}}}]$'.format(unit))
                plt.title(r'$\textbf{{{0} {1} Return Values Plot}}$'.format(name, self.distribution))
            else:
                plt.scatter(self.extremes['T'].values, self.extremes[self.col].values, s=20, linewidths=1,
                            marker='o', facecolor='None', edgecolors='royalblue', label=r'Extreme Values')
                plt.plot(self.retvalsum.index.values, self.retvalsum['Return Value'].values,
                         lw=2, color='orangered', label=r'{} Fit'.format(self.distribution))
                if confidence:
                    plt.fill_between(self.retvalsum.index.values, self.retvalsum['Upper'].values,
                                     self.retvalsum['Lower'].values, alpha=0.3, color='royalblue',
                                     label=r'95% confidence interval')
                plt.xscale('log')
                plt.xlabel(r'Return Period [years]')
                plt.ylabel(r'Return Value [{0}]'.format(unit))
                plt.title(r'{0} {1} Return Values Plot'.format(name, self.distribution))
            plt.xlim((0, self.retvalsum.index.values.max()))
            plt.ylim(ylim)
            plt.legend(loc=2)
            if save_path is not None:
                plt.savefig(save_path + '\{0} {1} Return Values Plot.png'.format(name, self.distribution),
                            bbox_inches='tight', dpi=600)
                plt.close()
            else:
                plt.show()

    def dens_fit_plot(self, distribution='GPD'):
        """
        Probability density plot. Histogram of extremes with fit overlay.

        :param distribution:
        :return:
        """
        print('Not yet implemented')
