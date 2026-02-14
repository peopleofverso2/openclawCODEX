<?php
/**
 * Plugin Name: AI Formatter (Clean Copy)
 * Description: Colle/importe un texte, nettoie les tics LLM, corrige orthographe + typographie FR, et applique un style CSS preset.
 * Version: 0.1.0
 * Author: OpenClaw
 * Text Domain: ai-formatter
 * Requires at least: 6.0
 * Requires PHP: 7.4
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'AIF_VERSION', '0.1.0' );
define( 'AIF_PATH', plugin_dir_path( __FILE__ ) );
define( 'AIF_URL', plugin_dir_url( __FILE__ ) );

require_once AIF_PATH . 'includes/clean.php';
require_once AIF_PATH . 'includes/typography.php';
require_once AIF_PATH . 'includes/markdown.php';
require_once AIF_PATH . 'includes/ai-provider.php';
require_once AIF_PATH . 'includes/settings.php';

/**
 * Register admin menu page under Tools.
 */
add_action( 'admin_menu', function () {
	add_submenu_page(
		'tools.php',
		__( 'AI Formatter', 'ai-formatter' ),
		__( 'AI Formatter', 'ai-formatter' ),
		'edit_posts',
		'ai-formatter',
		'aif_render_admin_page'
	);
} );

/**
 * Enqueue admin assets only on the plugin page.
 */
add_action( 'admin_enqueue_scripts', function ( $hook ) {
	if ( 'tools_page_ai-formatter' !== $hook ) {
		return;
	}
	wp_enqueue_style( 'aif-admin', AIF_URL . 'assets/admin.css', [], AIF_VERSION );
	wp_enqueue_script( 'aif-admin', AIF_URL . 'assets/admin.js', [ 'wp-api-fetch' ], AIF_VERSION, true );
	wp_localize_script( 'aif-admin', 'AIF', [
		'restUrl' => esc_url_raw( rest_url( 'ai-formatter/v1/format' ) ),
		'nonce'   => wp_create_nonce( 'wp_rest' ),
	] );
} );

/**
 * Render the admin page.
 */
function aif_render_admin_page() {
	$ai_configured = (bool) get_option( 'aif_api_key' );
	?>
	<div class="wrap">
		<h1><?php esc_html_e( 'AI Formatter', 'ai-formatter' ); ?></h1>

		<?php if ( ! $ai_configured ) : ?>
			<div class="notice notice-info">
				<p>
					<?php
					printf(
						/* translators: %s: URL to settings page */
						esc_html__( 'Mode IA non configure. Ajoutez votre cle API dans %s.', 'ai-formatter' ),
						'<a href="' . esc_url( admin_url( 'options-general.php?page=ai-formatter-settings' ) ) . '">' .
						esc_html__( 'Reglages', 'ai-formatter' ) . '</a>'
					);
					?>
				</p>
			</div>
		<?php endif; ?>

		<div class="aif-grid">
			<div class="aif-panel">
				<h2><?php esc_html_e( 'Texte source', 'ai-formatter' ); ?></h2>
				<textarea id="aif-input" rows="18" placeholder="<?php esc_attr_e( 'Colle ici ton texte...', 'ai-formatter' ); ?>"></textarea>

				<div class="aif-row">
					<label for="aif-mode"><?php esc_html_e( 'Mode', 'ai-formatter' ); ?></label>
					<select id="aif-mode">
						<option value="clean_only"><?php esc_html_e( 'Nettoyage + typographie (sans IA)', 'ai-formatter' ); ?></option>
						<option value="ai_proofread" <?php echo $ai_configured ? '' : 'disabled'; ?>>
							<?php esc_html_e( 'IA : correction orthographe + style', 'ai-formatter' ); ?>
						</option>
					</select>
				</div>

				<div class="aif-row" id="aif-style-row" style="display:none;">
					<label for="aif-style"><?php esc_html_e( 'Style', 'ai-formatter' ); ?></label>
					<select id="aif-style">
						<option value="neutral"><?php esc_html_e( 'Neutre', 'ai-formatter' ); ?></option>
						<option value="journalistic"><?php esc_html_e( 'Journalistique', 'ai-formatter' ); ?></option>
						<option value="corporate"><?php esc_html_e( 'Corporate', 'ai-formatter' ); ?></option>
					</select>
				</div>

				<div class="aif-row">
					<label for="aif-css"><?php esc_html_e( 'Preset CSS', 'ai-formatter' ); ?></label>
					<select id="aif-css">
						<option value="clean">Clean</option>
						<option value="sansdoute">SansDoute</option>
						<option value="tech">Tech Doc</option>
						<option value="apple">Apple Clean</option>
					</select>
				</div>

				<div class="aif-actions">
					<button class="button button-primary" id="aif-run">
						<?php esc_html_e( 'Nettoyer & Formater', 'ai-formatter' ); ?>
					</button>
					<button class="button" id="aif-copy" disabled>
						<?php esc_html_e( 'Copier HTML', 'ai-formatter' ); ?>
					</button>
				</div>

				<p class="description">
					<?php esc_html_e( 'Le mode IA necessite une cle API configuree dans les reglages.', 'ai-formatter' ); ?>
				</p>
			</div>

			<div class="aif-panel">
				<h2><?php esc_html_e( 'Resultat (HTML)', 'ai-formatter' ); ?></h2>
				<textarea id="aif-output" rows="18" readonly></textarea>

				<h2><?php esc_html_e( 'Previsualisation', 'ai-formatter' ); ?></h2>
				<div id="aif-preview" class="aif-preview aif-css-clean"></div>
			</div>
		</div>
	</div>
	<?php
}

/**
 * Register REST API route.
 */
add_action( 'rest_api_init', function () {
	register_rest_route( 'ai-formatter/v1', '/format', [
		'methods'             => 'POST',
		'permission_callback' => function () {
			return current_user_can( 'edit_posts' );
		},
		'callback'            => 'aif_rest_format',
		'args'                => [
			'text' => [
				'required'          => true,
				'type'              => 'string',
				'sanitize_callback' => 'sanitize_textarea_field',
			],
			'mode' => [
				'required' => false,
				'type'     => 'string',
				'default'  => 'clean_only',
				'enum'     => [ 'clean_only', 'ai_proofread' ],
			],
			'css' => [
				'required' => false,
				'type'     => 'string',
				'default'  => 'clean',
				'enum'     => [ 'clean', 'sansdoute', 'tech', 'apple' ],
			],
			'style' => [
				'required' => false,
				'type'     => 'string',
				'default'  => 'neutral',
				'enum'     => [ 'neutral', 'journalistic', 'corporate' ],
			],
		],
	] );
} );

/**
 * Handle format REST request.
 */
function aif_rest_format( WP_REST_Request $req ) {
	$text  = $req->get_param( 'text' );
	$mode  = $req->get_param( 'mode' );
	$css   = $req->get_param( 'css' );
	$style = $req->get_param( 'style' );

	if ( empty( trim( $text ) ) ) {
		return new WP_REST_Response( [ 'error' => 'Texte vide.' ], 400 );
	}

	// Layer 1: Clean LLM artifacts
	$clean = aif_clean_llm_artifacts( $text );

	// Layer 2: French typography
	$clean = aif_apply_french_typography( $clean );

	// Layer 3: Convert to HTML
	$html = aif_markdownish_to_html( $clean );

	// Layer 4 (optional): AI proofreading
	if ( 'ai_proofread' === $mode ) {
		$result = aif_ai_proofread( $html, $style );
		if ( is_wp_error( $result ) ) {
			return new WP_REST_Response(
				[ 'error' => $result->get_error_message() ],
				500
			);
		}
		$html = $result;
	}

	return new WP_REST_Response( [
		'html' => $html,
		'css'  => $css,
	], 200 );
}
