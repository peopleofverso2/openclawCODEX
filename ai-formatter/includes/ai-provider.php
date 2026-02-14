<?php
/**
 * AI provider integration for proofreading.
 *
 * Supports OpenAI and Anthropic APIs.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Send HTML to AI for proofreading and style correction.
 *
 * @param string $html  HTML content to proofread.
 * @param string $style Writing style: neutral, journalistic, corporate.
 * @return string|WP_Error Corrected HTML or error.
 */
function aif_ai_proofread( $html, $style = 'neutral' ) {
	$provider = get_option( 'aif_provider', 'openai' );
	$api_key  = get_option( 'aif_api_key', '' );

	if ( empty( $api_key ) ) {
		return new WP_Error( 'aif_no_key', __( 'Cle API non configuree. Allez dans Reglages > AI Formatter.', 'ai-formatter' ) );
	}

	$system_prompt = aif_build_system_prompt( $style );

	switch ( $provider ) {
		case 'anthropic':
			return aif_call_anthropic( $api_key, $system_prompt, $html );
		case 'openai':
		default:
			return aif_call_openai( $api_key, $system_prompt, $html );
	}
}

/**
 * Build the system prompt for AI proofreading.
 *
 * @param string $style Writing style.
 * @return string System prompt.
 */
function aif_build_system_prompt( $style ) {
	$style_instructions = [
		'neutral'       => 'Utilise un style neutre et clair, adapte a un large public.',
		'journalistic'  => 'Utilise un style journalistique : phrases courtes, actives, percutantes. Privilegle les faits.',
		'corporate'     => 'Utilise un style corporate professionnel : ton mesure, formulations polies et structurees.',
	];

	$style_text = $style_instructions[ $style ] ?? $style_instructions['neutral'];

	return <<<PROMPT
Tu es un correcteur professionnel en francais.

Regles strictes :
- Corrige toutes les fautes d'orthographe, grammaire et accords.
- Applique la typographie francaise (guillemets francais, espaces insecables, apostrophes courbes).
- {$style_text}
- Ne rajoute aucun preambule, aucune conclusion, aucun emoji, aucun commentaire.
- Ne modifie pas la structure HTML (balises h2, h3, p, ul, li, ol).
- Retourne UNIQUEMENT le HTML corrige, rien d'autre.
PROMPT;
}

/**
 * Call OpenAI Chat Completions API.
 *
 * @param string $api_key      API key.
 * @param string $system_prompt System prompt.
 * @param string $html         HTML to proofread.
 * @return string|WP_Error Corrected HTML.
 */
function aif_call_openai( $api_key, $system_prompt, $html ) {
	$response = wp_remote_post( 'https://api.openai.com/v1/chat/completions', [
		'timeout' => 60,
		'headers' => [
			'Authorization' => 'Bearer ' . $api_key,
			'Content-Type'  => 'application/json',
		],
		'body'    => wp_json_encode( [
			'model'       => get_option( 'aif_model', 'gpt-4o-mini' ),
			'messages'    => [
				[ 'role' => 'system', 'content' => $system_prompt ],
				[ 'role' => 'user', 'content' => $html ],
			],
			'temperature' => 0.3,
			'max_tokens'  => 4096,
		] ),
	] );

	if ( is_wp_error( $response ) ) {
		return $response;
	}

	$code = wp_remote_retrieve_response_code( $response );
	$body = json_decode( wp_remote_retrieve_body( $response ), true );

	if ( 200 !== $code ) {
		$msg = $body['error']['message'] ?? 'Erreur API OpenAI (HTTP ' . $code . ')';
		return new WP_Error( 'aif_openai_error', $msg );
	}

	return $body['choices'][0]['message']['content'] ?? $html;
}

/**
 * Call Anthropic Messages API.
 *
 * @param string $api_key      API key.
 * @param string $system_prompt System prompt.
 * @param string $html         HTML to proofread.
 * @return string|WP_Error Corrected HTML.
 */
function aif_call_anthropic( $api_key, $system_prompt, $html ) {
	$response = wp_remote_post( 'https://api.anthropic.com/v1/messages', [
		'timeout' => 60,
		'headers' => [
			'x-api-key'         => $api_key,
			'anthropic-version'  => '2023-06-01',
			'Content-Type'       => 'application/json',
		],
		'body'    => wp_json_encode( [
			'model'      => get_option( 'aif_model', 'claude-sonnet-4-20250514' ),
			'max_tokens' => 4096,
			'system'     => $system_prompt,
			'messages'   => [
				[ 'role' => 'user', 'content' => $html ],
			],
		] ),
	] );

	if ( is_wp_error( $response ) ) {
		return $response;
	}

	$code = wp_remote_retrieve_response_code( $response );
	$body = json_decode( wp_remote_retrieve_body( $response ), true );

	if ( 200 !== $code ) {
		$msg = $body['error']['message'] ?? 'Erreur API Anthropic (HTTP ' . $code . ')';
		return new WP_Error( 'aif_anthropic_error', $msg );
	}

	return $body['content'][0]['text'] ?? $html;
}
