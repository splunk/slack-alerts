export function generateMessageJSON({ from_user, from_user_icon, message = 'Lorem ipsum dolor sit amet.' }) {
    return {
        text: message,
        username: from_user,
        icon_url: from_user_icon,
    };
}

export function openSlackMessagePreview(data) {
    const url = `https://api.slack.com/docs/messages/builder?msg=${encodeURIComponent(
        JSON.stringify(generateMessageJSON(data))
    )}`;
    window.open(url);
}
