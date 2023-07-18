from bs4 import BeautifulSoup
import abc


class BaseParser:
    @abc.abstractmethod
    def parse(self, content):
        pass


class SalesDetailsParser(BaseParser):
    def parse(self, content):
        root_bs = BeautifulSoup(content, features="html.parser")
        headers = self._parse_headers(root_bs)
        rows = self._parse_rows(root_bs)
        items = []
        for row in rows:
            items.append(dict(zip(headers, row)))
        return headers, items

    def _parse_rows(self, bs):
        """first 3 trs and last 1 tr are headers"""
        trs = bs.find_all("tr")
        trs = trs[3:-1]
        return [[td.get_text().strip() for td in tr.find_all("td")] for tr in trs]

    def _parse_headers(self, bs):
        # first tr is useles header
        # second tr have headers but at 8th position there is  a colspan which can be replaces with all items in 3rd tr
        trs = bs.find_all("tr")

        trs.pop(0)
        ths = trs.pop(0).find_all("th")
        ths = ths[:6] + trs.pop(0).find_all("th") + ths[7:]
        return [th.get_text().strip() for th in ths]


class RCDetailParser(BaseParser):
    def parse(self, content):
        root_bs = BeautifulSoup(content, features="html.parser")
        tables = root_bs.find_all("table")
        # there might me 3 or 4 tables
        # first table is members table
        members = self._parse_members(tables[0])
        # last table is transactions table
        transactons = self._parse_transactions(tables[-1])
        return members, transactons

    def _parse_members(self, table):
        try:
            trs = table.find_all("tr")
            trs = trs[2:]
            headers = [th.get_text().strip() for th in trs.pop(0).find_all("th")]
            rows = [[td.get_text().strip() for td in tr.find_all("td")] for tr in trs]
        except Exception:
            return []
        else:
            return [dict(zip(headers, row)) for row in rows]

    def _parse_transactions(self, table):
        try:
            trs = table.find_all("tr")
            trs = trs[1:]
            tds = trs.pop(0).find_all("td")
            tds = tds[:-1] + trs.pop(0).find_all("td")
            headers = [td.get_text().strip() for td in tds]
            rows = [[td.get_text().strip() for td in tr.find_all("td")] for tr in trs]
        except Exception:
            return []
        else:
            return [dict(zip(headers, row)) for row in rows]


class StockDetailParser(BaseParser):
    def parse(self, content):
        root_bs = BeautifulSoup(content, features="html.parser")
        table = root_bs.find("table", attrs={"id": "stock_details"})
        if table is None:
            return []
        headers = self._parse_header(table)
        rows = self._parse_rows(table)
        return [dict(zip(headers, row)) for row in rows]

    def _parse_rows(self, table):
        trs = table.find_all("tr")
        trs = trs[3:]
        return [[td.get_text() for td in tr.find_all("td")] for tr in trs]

    def _parse_header(self, table):
        trs = table.find_all("tr")
        trs.pop(0)
        ths = trs.pop(0).find_all("th")
        next_ths = trs.pop(0).find_all("th")
        headers = []
        for th in ths:
            colspan = int(th.attrs.get("colspan", 0))
            if colspan:
                suffix = th.get_text()
                while colspan and len(next_ths):
                    header = next_ths.pop(0).get_text()
                    headers.append(f"{header} {suffix}")
            else:
                headers.append(th.get_text())
        return headers


class EPDSRCDetailParser(BaseParser):
    def parse(self, content):
        root_bs = BeautifulSoup(content, features="html.parser")
        selector = {"id": "ContentPlaceHolder2_gridview_member"}
        table = root_bs.find("table", selector)
        headers = self._parse_header(table) if table else []
        members = self._parse_members(table) if table else []
        extra = self._parse_extra_info(table, root_bs)
        return [dict(zip(headers, member)) for member in members], extra

    def _parse_members(self, table):
        trs = table.find_all("tr")
        # members trs start from 4th tr
        trs = trs[3:]
        return [[td.get_text().strip() for td in tr.find_all("td")] for tr in trs]

    def _parse_header(self, table):
        trs = table.find_all("tr")
        header_tr = trs[2]
        ths = header_tr.find_all("th")
        return [th.get_text().strip() for th in ths]

    def _parse_extra_info(self, table, root_bs):
        extra = {}
        if table:
            trs = table.find_all("tr")
            # extra info tr is 2nd tr, EPDS FPS Code, Scheme and No. of Units
            info_tr = trs[1]
            for th in info_tr.find_all("th"):
                segments = th.get_text().strip().split(":")
                if len(segments) > 1:
                    extra[segments[0].strip()] = ' '.join([s.strip() for s in segments[1:]])
        state_span = root_bs.find("span", {"id": "ContentPlaceHolder2_lbldistcode1"})
        if state_span:
            extra["Message"] = state_span.get_text().strip()
        return extra

