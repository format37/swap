"""The bot's strings in Russian, English and Georgian (ADR-0009).

The Mini App's strings live in `frontend/src/i18n/`. These are only the ones the bot
writes itself. The Georgian still needs a native speaker's read before MVP acceptance.
"""

from decimal import Decimal
from typing import Literal, get_args

type Locale = Literal["ru", "en", "ka"]
LOCALES: tuple[Locale, ...] = get_args(Locale.__value__)
# What anyone whose Telegram speaks none of the three gets.
DEFAULT_LOCALE: Locale = "en"


def resolve_locale(chosen: str | None, language_code: str | None) -> Locale:
    """The language picked in the app, else Telegram's, else English.

    Telegram sends IETF tags ("pt-br"), so only the primary subtag counts.
    """
    for candidate in (chosen, (language_code or "").split("-")[0].lower()):
        for locale in LOCALES:
            if candidate == locale:
                return locale
    return DEFAULT_LOCALE


MESSAGES: dict[Locale, dict[str, str]] = {
    "ru": {
        "start.greeting": (
            "Привет, {name}! Swap помогает договориться об обмене денег между странами "
            "с теми, кого вы знаете: вы платите их получателю у себя, они — вашему у "
            "себя. Swap не хранит и не переводит деньги: он только планирует и "
            "записывает."
        ),
        "start.hint": "Всё происходит в приложении. Откройте его кнопкой ниже.",
        "button.open": "Открыть Swap",
        "button.open_card": "Открыть",
        "invite.requested": (
            "{name} приглашает вас в Swap.\n\n"
            "Swap помогает знакомым договариваться об обмене денег между странами: каждый "
            "платит получателю другого у себя. Сам Swap деньги не хранит и не переводит, "
            "он только планирует и записывает.\n\n"
            "Откройте приглашение, чтобы установить связь или отклонить его."
        ),
        "link.requested": (
            "{name} хочет установить с вами связь в Swap. Связанные видят заявки друг "
            "друга, открытые для связей."
        ),
        "link.established": (
            "Связь установлена: {name}. Теперь вы видите заявки друг друга, открытые для связей."
        ),
        "order.opened": (
            "{name} — новая заявка № {number}. Отдаёт: до {amount} {currency}. "
            "Взамен хочет: {wants}."
        ),
        "invite.already_linked": "Связь уже есть: {name}.",
        "invite.own": (
            "Это ваша собственная ссылка-приглашение. Отправьте её тому, кого хотите пригласить."
        ),
        "invite.invalid": (
            "Это приглашение больше не действует: оно истекло, отозвано или уже "
            "использовано. Попросите прислать новое."
        ),
        "deal.proposed": (
            "{name} предлагает сделку по вашей заявке № {number}: вы отдаёте {amount} "
            "{currency}, получаете {counter_amount} {counter_currency}. Откройте, чтобы "
            "принять или отклонить; предложение действует 48 часов."
        ),
        "deal.accepted": (
            "Сделка принята — {name}. Откройте её: там видно, кто, что и когда отправляет."
        ),
        "deal.declined": "Предложение отклонено — {name}.",
        "deal.withdrawn": "Предложение отозвано — {name}.",
        "deal.expired": "Предложение истекло без ответа — {name}.",
        "deal.cancelled": "Сделка отменена — {name}.",
        "deal.proposal_closed": (
            "Предложение отменено: заявка закрыта или её остатка не хватает — {name}."
        ),
        "deal.sent": (
            "Отправлено: {amount} {currency} — {name}. Проверьте поступление и отметьте «Получено»."
        ),
        "deal.received": "Получение подтверждено: {amount} {currency} — {name}.",
        "deal.settled": "Сделка завершена: получение {amount} {currency} подтверждено — {name}.",
        "export.caption": (
            "Ваши сделки в Swap: {count}. Файл CSV открывается в Excel, Numbers и Google Таблицах."
        ),
        "export.header": (
            "Предложена|Принята|Закрыта|Заявка №|Статус|С кем|Отдано: сумма|Отдано: валюта|"
            "Отдано: страна|Отдано: как|Получено: сумма|Получено: валюта|Получено: страна|"
            "Получено: как|Курс|Источник курса"
        ),
        "export.status.proposed": "предложена",
        "export.status.accepted": "принята",
        "export.status.disputed": "спор",
        "export.status.settled": "завершена",
        "export.status.cancelled": "отменена",
        "export.status.expired": "истекла",
        "export.way.cash": "наличные",
        "export.way.bank": "банк",
        "export.way.crypto": "крипто",
        "export.rate.author": "курс автора заявки",
        "export.rate.market": "Coinbase, {time}",
        "export.deleted": "Удалённый участник",
        "bot.command.start": "Открыть Swap",
        "bot.short_description": (
            "Обмен деньгами между странами с людьми, которых вы знаете. Swap планирует "
            "и записывает, но не хранит деньги."
        ),
        "bot.description": (
            "Swap помогает знакомым людям договориться о встречных переводах: у вас "
            "рубли в России, у знакомого — лари в Грузии, и каждый платит получателю "
            "другого у себя. Заявки видны по цепочке приглашений — так далеко, как "
            "разрешил их автор. Swap не хранит, не переводит и не гарантирует деньги: "
            "он ведёт сделку по шагам и показывает, кто кому должен."
        ),
    },
    "en": {
        "start.greeting": (
            "Hi, {name}! Swap helps you arrange money swaps across countries with people "
            "you know: you pay their recipient where you are, they pay yours where they "
            "are. Swap never holds or moves money; it only plans and records."
        ),
        "start.hint": "Everything happens in the app. Open it with the button below.",
        "button.open": "Open Swap",
        "button.open_card": "Open",
        "invite.requested": (
            "{name} invites you to Swap.\n\n"
            "Swap helps people who know each other arrange money swaps across countries: "
            "each pays the other's recipient at home. Swap itself never holds or moves "
            "money; it only plans and records.\n\n"
            "Open the invitation to link up or to decline it."
        ),
        "link.requested": (
            "{name} wants to link with you in Swap. Linked people see each other's offers "
            "that are open to links."
        ),
        "link.established": (
            "Linked: {name}. You now see each other's offers that are open to links."
        ),
        "order.opened": (
            "{name} — new offer No. {number}. Gives: up to {amount} {currency}. "
            "Wants in return: {wants}."
        ),
        "invite.already_linked": "You are already linked: {name}.",
        "invite.own": (
            "This is your own invitation link. Send it to the person you want to invite."
        ),
        "invite.invalid": (
            "This invitation no longer works: it expired, was revoked or has already been "
            "used. Ask for a new one."
        ),
        "deal.proposed": (
            "{name} proposes a deal on your offer No. {number}: you give {amount} {currency} "
            "and get {counter_amount} {counter_currency}. Open it to accept or decline; the "
            "proposal stands for 48 hours."
        ),
        "deal.accepted": "Deal accepted — {name}. Open it to see who sends what, and when.",
        "deal.declined": "Proposal declined — {name}.",
        "deal.withdrawn": "Proposal withdrawn — {name}.",
        "deal.expired": "Proposal expired unanswered — {name}.",
        "deal.cancelled": "Deal cancelled — {name}.",
        "deal.proposal_closed": (
            "Proposal cancelled: the offer is closed or has too little left — {name}."
        ),
        "deal.sent": (
            "Sent: {amount} {currency} — {name}. Check it has arrived and mark it “Received”."
        ),
        "deal.received": "Receipt confirmed: {amount} {currency} — {name}.",
        "deal.settled": "Deal complete: receipt of {amount} {currency} confirmed — {name}.",
        "export.caption": (
            "Your deals in Swap: {count}. The CSV file opens in Excel, Numbers and Google Sheets."
        ),
        "export.header": (
            "Proposed|Accepted|Closed|Offer No.|Status|With|Gave: amount|Gave: currency|"
            "Gave: country|Gave: way|Got: amount|Got: currency|Got: country|Got: way|Rate|"
            "Rate source"
        ),
        "export.status.proposed": "proposed",
        "export.status.accepted": "accepted",
        "export.status.disputed": "disputed",
        "export.status.settled": "settled",
        "export.status.cancelled": "cancelled",
        "export.status.expired": "expired",
        "export.way.cash": "cash",
        "export.way.bank": "bank",
        "export.way.crypto": "crypto",
        "export.rate.author": "the offer author's rate",
        "export.rate.market": "Coinbase, {time}",
        "export.deleted": "Former member",
        "bot.command.start": "Open Swap",
        "bot.short_description": (
            "Swap money across countries with people you know. Swap plans and records; "
            "it never holds money."
        ),
        "bot.description": (
            "Swap helps people who know each other arrange counter-transfers: you have "
            "roubles in Russia, a friend has lari in Georgia, and each of you pays the "
            "other's recipient at home. Offers travel along chains of invitations, as "
            "far as their authors allow. Swap never holds, moves or guarantees money: it "
            "walks the deal step by step and shows who owes whom."
        ),
    },
    "ka": {
        "start.greeting": (
            "გამარჯობა, {name}! Swap გეხმარებათ, ნაცნობებთან შეთანხმდეთ ფულის გაცვლაზე "
            "ქვეყნებს შორის: თქვენ უხდით მათ მიმღებს თქვენთან, ისინი კი თქვენსას — "
            "მათთან. Swap არ ინახავს და არ გადარიცხავს ფულს: ის მხოლოდ გეგმავს და "
            "აღრიცხავს."
        ),
        "start.hint": "ყველაფერი აპლიკაციაში ხდება. გახსენით ის ქვემოთ მოცემული ღილაკით.",
        "button.open": "Swap-ის გახსნა",
        "button.open_card": "გახსნა",
        "invite.requested": (
            "{name} გიწვევთ Swap-ში.\n\n"
            "Swap ეხმარება ნაცნობებს, შეთანხმდნენ ფულის გაცვლაზე ქვეყნებს შორის: "
            "თითოეული უხდის მეორის მიმღებს საკუთარ ქვეყანაში. თავად Swap ფულს არ ინახავს "
            "და არ გადარიცხავს, ის მხოლოდ გეგმავს და აღრიცხავს.\n\n"
            "გახსენით მოწვევა, რომ დაუკავშირდეთ ან უარი თქვათ."
        ),
        "link.requested": (
            "{name} გთხოვთ, დაუკავშირდეთ Swap-ში. დაკავშირებულები ხედავენ ერთმანეთის "
            "განცხადებებს, რომლებიც კავშირებისთვისაა გახსნილი."
        ),
        "link.established": (
            "კავშირი დამყარდა: {name}. ახლა ერთმანეთის განცხადებებს ხედავთ, რომლებიც "
            "კავშირებისთვისაა გახსნილი."
        ),
        "order.opened": (
            "{name} — ახალი განცხადება № {number}. გასცემს: მაქსიმუმ {amount} {currency}. "
            "სანაცვლოდ სურს: {wants}."
        ),
        "invite.already_linked": "კავშირი უკვე არსებობს: {name}.",
        "invite.own": (
            "ეს თქვენი საკუთარი მოსაწვევი ბმულია. გაუგზავნეთ ის მას, ვისი მოწვევაც გსურთ."
        ),
        "invite.invalid": (
            "ეს მოწვევა აღარ მოქმედებს: ვადა გაუვიდა, გაუქმდა ან უკვე გამოყენებულია. სთხოვეთ ახალი."
        ),
        "deal.proposed": (
            "{name} გთავაზობთ გარიგებას თქვენს განცხადებაზე № {number}: გასცემთ {amount} "
            "{currency}, მიიღებთ {counter_amount} {counter_currency}. გახსენით, რომ მიიღოთ ან "
            "უარყოთ; შეთავაზება 48 საათი მოქმედებს."
        ),
        "deal.accepted": (
            "გარიგება მიღებულია — {name}. გახსენით, რომ ნახოთ, ვინ რას და როდის აგზავნის."
        ),
        "deal.declined": "შეთავაზება უარყოფილია — {name}.",
        "deal.withdrawn": "შეთავაზება გაუქმებულია — {name}.",
        "deal.expired": "შეთავაზებას ვადა პასუხის გარეშე გაუვიდა — {name}.",
        "deal.cancelled": "გარიგება გაუქმდა — {name}.",
        "deal.proposal_closed": (
            "შეთავაზება გაუქმდა: განცხადება დახურულია ან მისი ნაშთი არ ჰყოფნის — {name}."
        ),
        "deal.sent": (
            "გაგზავნილია: {amount} {currency} — {name}. შეამოწმეთ ჩარიცხვა და მონიშნეთ „მიღებულია“."
        ),
        "deal.received": "მიღება დადასტურებულია: {amount} {currency} — {name}.",
        "deal.settled": "გარიგება დასრულდა: მიღება დადასტურებულია, {amount} {currency} — {name}.",
        "export.caption": (
            "თქვენი გარიგებები Swap-ში: {count}. CSV ფაილი იხსნება Excel-ში, Numbers-სა და "
            "Google Sheets-ში."
        ),
        "export.header": (
            "შეთავაზებულია|მიღებულია|დახურულია|განცხადება №|სტატუსი|ვისთან|გაცემული: თანხა|"
            "გაცემული: ვალუტა|გაცემული: ქვეყანა|გაცემული: როგორ|მიღებული: თანხა|"
            "მიღებული: ვალუტა|მიღებული: ქვეყანა|მიღებული: როგორ|კურსი|კურსის წყარო"
        ),
        "export.status.proposed": "შეთავაზებული",
        "export.status.accepted": "მიღებული",
        "export.status.disputed": "დავა",
        "export.status.settled": "დასრულებული",
        "export.status.cancelled": "გაუქმებული",
        "export.status.expired": "ვადაგასული",
        "export.way.cash": "ნაღდი",
        "export.way.bank": "ბანკი",
        "export.way.crypto": "კრიპტო",
        "export.rate.author": "განცხადების ავტორის კურსი",
        "export.rate.market": "Coinbase, {time}",
        "export.deleted": "წაშლილი მონაწილე",
        "bot.command.start": "Swap-ის გახსნა",
        "bot.short_description": (
            "ფულის გაცვლა ქვეყნებს შორის ნაცნობებთან. Swap გეგმავს და აღრიცხავს, ფულს არ ინახავს."
        ),
        "bot.description": (
            "Swap ეხმარება ნაცნობ ადამიანებს, შეთანხმდნენ ურთიერთგადარიცხვებზე: თქვენ "
            "გაქვთ რუბლი რუსეთში, თქვენს ნაცნობს — ლარი საქართველოში, და თითოეული "
            "უხდის მეორის მიმღებს საკუთარ ქვეყანაში. განცხადებები მოწვევების ჯაჭვით "
            "ვრცელდება, იმდენად შორს, რამდენადაც ავტორი დაუშვებს. Swap არ ინახავს, "
            "არ გადარიცხავს და არ იძლევა ფულის გარანტიას: ის ნაბიჯ-ნაბიჯ მიჰყვება "
            "გარიგებას და აჩვენებს, ვინ ვის რა მართებს."
        ),
    },
}


def t(locale: Locale, key: str, **values: str) -> str:
    """The string for `key` in `locale`, with `{placeholders}` filled in."""
    return MESSAGES[locale][key].format(**values)


def format_amount(amount: Decimal, locale: Locale) -> str:
    """«150 000» and «1 712,33»; in English «150,000» and «1,712.33». Whole amounts drop
    their cents. Georgian groups and marks decimals as Russian does (ADR-0015). The app's
    Intl.NumberFormat writes the same."""
    text = f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"
    if locale == "en":
        return text
    # A no-break space, as Intl's ru-RU writes it, so an amount never splits a line.
    return text.replace(",", "\u00a0").replace(".", ",")
